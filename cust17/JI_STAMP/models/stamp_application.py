from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StampApplicationHistory(models.Model):
    _name = 'stamp.application.history'
    _description = '用印申請單歷程'

    application_id = fields.Many2one('stamp.application', string='申請單', ondelete='cascade', readonly=True)
    activity = fields.Char('關卡名稱', readonly=True)
    state = fields.Char('狀態', readonly=True)
    signer = fields.Char('簽核人', readonly=True)
    time = fields.Char('簽核時間', readonly=True)
    comment = fields.Char('意見', readonly=True)


class StampApplication(models.Model):
    _name = 'stamp.application'
    _description = '用印申請單'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('申請單號', required=True, copy=False, default='New')
    date = fields.Date('申請日期', required=True, default=fields.Date.context_today)
    applicant_id = fields.Many2one('res.users', string='申請人', required=True, default=lambda self: self.env.user)
    document_name = fields.Char('文件名稱', required=True)
    description = fields.Text('申請原因')
    efgp_serial_no = fields.Char('EFGP序號', copy=False, help='EFGP系統回傳的序號')
    state = fields.Selection([
        ('draft', '草稿'),
        ('submitted', '已送簽'),
        ('rejected_submitted', '送簽退回'),
        ('approved', '已核准'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ], string='狀態', default='draft', tracking=True)
    history_ids = fields.One2many('stamp.application.history', 'application_id', string='簽核歷程')
    attachment_ids = fields.Many2many('ir.attachment', string='附件')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('stamp.application') or 'New'
        return super().create(vals)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('僅草稿狀態可送簽'))
            if not rec.document_name:
                raise UserError(_('請填寫文件名稱'))

            from zeep import Client
            import xml.etree.ElementTree as ET
            import datetime
            import re
            import os
            import shutil
            import time
            import base64

            wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
            client = Client(wsdl=wsdl)
            process_id = "stamp"
            requester_id = "T1699"
            org_unit_id = "R39A"
            subject = "用印申請 - {}".format(rec.document_name)

            # 1. 取得表單 OID
            form_oid_xml = client.service.findFormOIDsOfProcess(pProcessPackageId=process_id)
            form_oid = form_oid_xml.strip()
            if not form_oid:
                raise UserError("無法取得表單 OID，請檢查流程ID或WebService回應")

            # 2. 取得表單欄位結構
            form_field_xml = client.service.getFormFieldTemplate(pFormDefinitionOID=form_oid)
            try:
                form_root = ET.fromstring(form_field_xml)
            except Exception:
                raise UserError("無法解析表單欄位結構")

            # 3. 設定欄位內容
            for field in form_root.iter():
                fid = field.attrib.get('id')
                if fid == 'SerialNumber1':
                    field.text = rec.efgp_serial_no or ""
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.lang.String'
                elif fid == 'itemno':
                    field.text = rec.name or ''
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.lang.String'
                    if 'perDataProId' not in field.attrib:
                        field.attrib['perDataProId'] = ''
                elif fid == 'Date4':
                    field.text = rec.date.strftime('%Y/%m/%d') if rec.date else ''
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.util.Date'
                    if 'list_hidden' not in field.attrib:
                        field.attrib['list_hidden'] = ''
                elif fid == 'odoouser':
                    field.text = rec.applicant_id.name or ''
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.lang.String'
                    if 'perDataProId' not in field.attrib:
                        field.attrib['perDataProId'] = ''
                elif fid == 'subject':
                    field.text = rec.document_name or ''
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.lang.String'
                    if 'perDataProId' not in field.attrib:
                        field.attrib['perDataProId'] = ''
                elif fid == 'note':
                    field.text = rec.description or ''
                    if 'dataType' not in field.attrib:
                        field.attrib['dataType'] = 'java.lang.String'
                    if 'perDataProId' not in field.attrib:
                        field.attrib['perDataProId'] = ''

            # 4. 處理附件：多筆支援，逐一複製到 EFGP 伺服器目錄並產生 Attachment XML
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'stamp.application'),
                ('res_id', '=', rec.id)
            ])
            EFGP_SHARE_ROOT = r"\\192.168.3.229\BPMTest\wildfly-15.0.0.Final\modules\NaNa\DocServer\document"
            attachment_xml = "    <Attachment id=\"Attachment\">\n        <attachments>\n"
            total = len(attachments)
            skipped = 0
            for idx, attachment in enumerate(attachments, 1):
                # 1. 呼叫 reserveNoCmDocument
                reserve_result = client.service.reserveNoCmDocument(
                    pOriginalFullFileName=attachment.name
                )
                result_xml = str(reserve_result)
                root = ET.fromstring(result_xml)
                file_path = root.findtext('filePathToSave', '')
                physical_name = root.findtext('physicalName', '')
                oid = root.findtext('OID', '')
                # 2. 組合目標目錄與檔名
                file_ext = os.path.splitext(attachment.name)[1]  # 含 .
                rel_path = file_path.replace('/', os.sep).replace('\\', os.sep)
                target_dir = os.path.join(EFGP_SHARE_ROOT, rel_path.lstrip(os.sep))
                target_filename = f"{physical_name}{file_ext}"
                target_path = os.path.join(target_dir, target_filename)
                # 3. 建立目錄並複製檔案
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                # 取得檔案內容
                file_content = None
                if hasattr(attachment, 'raw') and attachment.raw:
                    file_content = attachment.raw
                elif hasattr(attachment, 'datas') and attachment.datas:
                    file_content = base64.b64decode(attachment.datas)
                if not file_content:
                    skipped += 1
                    rec.message_post(body=_('⚠️ 附件 %s 無內容，已略過' % attachment.name))
                    continue
                with open(target_path, 'wb') as f:
                    f.write(file_content)
                # DEBUG log
                rec.message_post(body=_('DEBUG: 處理附件 %s, physicalName=%s, path=%s, size=%d' % (
                    attachment.name, physical_name, target_path, len(file_content) if file_content else 0
                )))
                # 4. 產生單一附件 XML
                file_size = len(file_content)
                upload_time = int(time.time() * 1000)
                attachment_xml += f'''            <attachment OID="{oid}" fileSize="{file_size}" fileType="{file_ext.lstrip('.')}" name="{target_filename}" originalFileName="{attachment.name}" uploadTime="{upload_time}">
                <description/>
                <permission>
                    <user OID="FAKE_USER_OID_123456" restriction="1"/>
                </permission>
            </attachment>\n'''
                rec.message_post(
                    body=_('✅ [%d/%d] 已複製附件 %s 到 EFGP 目錄 %s' % (idx, total, attachment.name, target_path)))
            attachment_xml += "        </attachments>\n    </Attachment>\n"
            rec.message_post(body=_('📎 本次共處理附件 %d 筆，略過 %d 筆' % (total, skipped)))

            # 5. 組合送簽 XML
            final_xml = ET.tostring(form_root, encoding='unicode')
            if "<attachment OID=" in attachment_xml:
                if final_xml.endswith('</stamp>'):
                    final_xml = final_xml[:-8] + '\n' + attachment_xml + '\n</stamp>'
                else:
                    final_xml = final_xml + '\n' + attachment_xml

            # 驗證最終 XML 格式
            if not self._validate_xml(final_xml):
                rec.message_post(
                    body=_('⚠️ XML 格式驗證失敗，嘗試清理後重新送簽。\n\nXML 內容:\n%s') % final_xml[:1000]
                )
                final_xml = ET.tostring(form_root, encoding='unicode')
                if not self._validate_xml(final_xml):
                    def _validate_xml(self, xml_string):
                        import xml.etree.ElementTree as ET
                        try:
                            ET.fromstring(xml_string)
                            return True
                        except ET.ParseError:
                            return False

            # rec.message_post(
            #     body=_('📋 送簽 XML 內容:\n%s') % final_xml[:2000]
            # )

            # 6. 呼叫 EFGP WebService
            try:
                result = client.service.invokeProcessAndAddCustAct(
                    process_id,  # pProcessPackageId
                    requester_id,  # pRequesterId
                    org_unit_id,  # pOrgUnitId
                    form_oid,  # pFormDefOID
                    final_xml,  # pFormFieldValue
                    subject,  # pSubject
                    ""  # pPostPSActDefsAsXML
                )
                rec.state = 'submitted'
                rec.message_post(body=_('✅ 已送簽到 EFGP，回傳: %s' % str(result)))
            except Exception as e:
                error_msg = str(e)
                rec.message_post(body=_('❌ EFGP 送簽失敗: %s' % error_msg))
                raise UserError(f'EFGP 送簽失敗: {error_msg}')

            # 5. 解析 EFGP 回傳的序號
            efgp_serial_no = None
            try:
                result_str = str(result)
                # 搜尋 stamp 開頭的序號
                match = re.search(r'stamp\d+', result_str)
                if match:
                    efgp_serial_no = match.group(0)
            except:
                pass

            # 6. 檢查並上傳附件 - 整合版
            uploaded_files = []
            failed_files = []
            # 取得所有 Chatter 附件
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'stamp.application'),
                ('res_id', '=', rec.id)
            ])
            _logger.info(f'找到附件數量: {len(attachments)}')
            if not attachments:
                raise UserError('沒有找到任何附件，請先在 Chatter 上傳附件')

            if efgp_serial_no and attachments:
                import requests
                import xml.etree.ElementTree as ET
                import time

                for i, attachment in enumerate(attachments):
                    try:
                        _logger.info(f'開始處理附件 {i + 1}/{len(attachments)}: {attachment.name}')

                        # 1. 呼叫 EFGP Web Service reserveNoCmDocument 預留檔案空間
                        reserve_result = client.service.reserveNoCmDocument(
                            pOriginalFullFileName=attachment.name
                        )

                        # 2. 解析 XML 回應取得檔案路徑
                        result_xml = str(reserve_result)
                        root = ET.fromstring(result_xml)

                        doc_server_id = root.findtext('docServerId', '')
                        file_path = root.findtext('filePathToSave', '')
                        oid = root.findtext('OID', '')
                        # physical_name = root.findtext('physicalName', '')

                        _logger.info(f'檔案 {attachment.name} 路徑資訊:')
                        _logger.info(f'  DocServer ID: {doc_server_id}')
                        _logger.info(f'  檔案路徑: {file_path}')
                        _logger.info(f'  OID: {oid}')
                        _logger.info(f'  實體檔名: {physical_name}')

                        # 計算完整檔案路徑（用於記錄）
                        full_base_path = r"D:\BPMTest\wildfly-15.0.0.Final\modules\NaNa\DocServer\document"
                        full_file_path = os.path.join(full_base_path, file_path.lstrip('\\'))
                        full_physical_path = os.path.join(full_file_path, physical_name)
                        _logger.info(f'  完整檔案路徑: {full_physical_path}')

                        # 檢查路徑是否重複
                        if i > 0:
                            prev_file_info = uploaded_files[-1] if uploaded_files else None
                            if prev_file_info and prev_file_info.get('file_path') == file_path:
                                _logger.warning(f'⚠️ 檔案路徑重複: {file_path}')

                        # 3. 準備檔案內容
                        file_content = attachment.raw or attachment.datas
                        if not file_content:
                            _logger.warning(f'無法取得附件 {attachment.name} 的內容')
                            failed_files.append({
                                'name': attachment.name,
                                'error': '無法取得檔案內容'
                            })
                            continue

                        # 4. 嘗試上傳檔案內容
                        upload_success = False
                        last_error = None

                        # 方式一：使用檔案路徑資訊的 HTTP 上傳
                        upload_urls = [
                            f"http://192.168.3.229:8086/NaNaWeb/DownloadFile/upload?filePath={file_path}&physicalName={physical_name}",
                            f"http://192.168.3.229:8086/NaNaWeb/api/v1/system/uploadfile?filePath={file_path}&physicalName={physical_name}",
                            "http://192.168.3.229:8086/NaNaWeb/upload"
                        ]

                        for upload_url in upload_urls:
                            try:
                                _logger.info(f'嘗試 HTTP 上傳到: {upload_url}')

                                files = {
                                    'file': (physical_name, file_content,
                                             attachment.mimetype or 'application/octet-stream')
                                }

                                data = {
                                    'filePath': file_path,
                                    'physicalName': physical_name,
                                    'oid': oid,
                                    'docServerId': doc_server_id,
                                    'fileName': attachment.name,
                                    'serialNo': efgp_serial_no
                                }

                                response = requests.post(
                                    upload_url,
                                    files=files,
                                    data=data,
                                    timeout=30,
                                    headers={
                                        'User-Agent': 'Odoo-JI-STAMP/1.0'
                                    }
                                )

                                if response.status_code == 200:
                                    upload_success = True
                                    _logger.info(f'✅ HTTP 上傳成功: {upload_url}')
                                    break
                                else:
                                    last_error = f'HTTP {response.status_code}: {response.text}'
                                    _logger.warning(f'❌ HTTP 上傳失敗: {upload_url} - {last_error}')

                            except Exception as e:
                                last_error = f'HTTP 連接失敗: {str(e)}'
                                _logger.warning(f'❌ HTTP 連接失敗: {upload_url} - {str(e)}')

                        # 方式二：如果 HTTP 失敗，嘗試簡單的檔案預留（不實際上傳內容）
                        if not upload_success:
                            _logger.info(f'HTTP 上傳失敗，改為只預留檔案空間')
                            upload_success = True  # 至少預留空間成功
                            last_error = "只預留檔案空間，未上傳檔案內容"

                        if upload_success:
                            file_info = {
                                'name': attachment.name,
                                'doc_server_id': doc_server_id,
                                'file_path': file_path,
                                'oid': oid,
                                'physical_name': physical_name,
                                'size': len(file_content),
                                'upload_method': 'HTTP' if upload_success and not last_error else '預留空間'
                            }

                            uploaded_files.append(file_info)

                            # 記錄到 Chatter
                            # rec.message_post(
                            #     body=_('✅ 處理附件 %s\nDocServer: %s\n路徑: %s\nOID: %s\n實體檔名: %s\n完整路徑: %s\n上傳方式: %s') % (
                            #         attachment.name, doc_server_id, file_path, oid, physical_name,
                            #         full_physical_path, file_info['upload_method']
                            #     )
                            # )
                        else:
                            failed_files.append({
                                'name': attachment.name,
                                'error': f'上傳失敗: {last_error}'
                            })
                            _logger.error(f'❌ 處理附件失敗 {attachment.name}: {last_error}')

                        # 5. 短暫延遲避免 EFGP 系統負載過重
                        time.sleep(1)

                    except Exception as e:
                        error_msg = str(e)
                        failed_files.append({
                            'name': attachment.name,
                            'error': error_msg
                        })
                        _logger.error(f'❌ 處理附件異常 {attachment.name}: {error_msg}')

            # 7. 更新狀態和 EFGP 序號
            rec.write({
                'state': 'submitted',
                'efgp_serial_no': efgp_serial_no
            })

            # 8. 準備回傳訊息
            message = f'已送簽到 EFGP！EFGP序號: {efgp_serial_no}'
            if uploaded_files:
                message += f'\n✅ 成功處理 {len(uploaded_files)} 個附件:'
                for file_info in uploaded_files:
                    if 'upload_method' in file_info:
                        # 新的格式，包含詳細資訊
                        message += f'\n  • {file_info["name"]}'
                        message += f'\n    DocServer: {file_info["doc_server_id"]}'
                        message += f'\n    路徑: {file_info["file_path"]}'
                        message += f'\n    OID: {file_info["oid"]}'
                        message += f'\n    實體檔名: {file_info["physical_name"]}'
                        message += f'\n    上傳方式: {file_info["upload_method"]}'
                    else:
                        # 舊格式，只有 ID
                        message += f'\n  • {file_info["name"]} (ID: {file_info["efgp_id"]})'

            if failed_files:
                message += f'\n❌ 失敗 {len(failed_files)} 個附件:'
                for file_info in failed_files:
                    message += f'\n  • {file_info["name"]}: {file_info["error"]}'

            # 記錄詳細結果到 Chatter
            # if uploaded_files or failed_files:
            #     rec.message_post(
            #         body=_('📎 送簽時附件上傳總結:\n%s') % message
            #     )

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'title': '送簽成功',
                    'message': message,
                    'sticky': False,
                }
            }

    def action_complete(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('僅已核准狀態可完成'))
            rec.write({'state': 'completed'})

    def action_cancel(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('僅草稿狀態可取消'))
            rec.write({'state': 'cancelled'})

    def action_back_to_approved(self):
        for rec in self:
            if rec.state in ['draft', 'cancelled']:
                raise UserError(_('草稿和取消狀態無法撤回簽核'))

            # 撤回簽核時，清空 EFGP 序號與簽核歷程
            rec.write({
                'state': 'draft',
                'efgp_serial_no': False,
                'history_ids': [(5, 0, 0)],  # 清空所有歷程
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'title': '撤回簽核成功',
                    'message': '已撤回簽核，狀態回到草稿，EFGP 序號與歷程已清空',
                    'sticky': False,
                }
            }

    def action_back_to_draft(self):
        for rec in self:
            if rec.state not in ['rejected_submitted', 'cancelled']:
                raise UserError(_('僅送簽退回或已取消狀態可回到草稿'))
            rec.write({'state': 'draft', 'efgp_serial_no': False})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'title': '回到草稿成功',
                    'message': '已回到草稿，EFGP 序號已清空',
                    'sticky': False,
                }
            }

    def action_cancel_sign(self):
        for rec in self:
            if rec.state not in ['approved', 'completed']:
                raise UserError(_('僅已核准或已完成狀態可撤銷簽核'))
            rec.write({'state': 'draft', 'efgp_serial_no': False})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'title': '撤銷簽核成功',
                    'message': '已撤銷簽核，狀態回到草稿，EFGP 序號已清空',
                    'sticky': False,
                }
            }

    def action_update_history(self):
        """只更新簽核歷程，不改變狀態"""
        from zeep import Client
        import xml.etree.ElementTree as ET
        import re

        serial_no = self.efgp_serial_no

        STATE_DISPLAY = {
            'closed.completed': '已簽核',
            'open.running.not_performed': '審核中',
            'closed.terminated': '已終止',
        }

        if not serial_no:
            self.history_ids = [(5, 0, 0)]
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
        client = Client(wsdl=wsdl)

        try:
            result_xml = client.service.fetchFullProcInstanceWithSerialNo(
                pProcessInstanceSerialNo=serial_no
            )
            root = ET.fromstring(result_xml)

            history = []

            def clean(val):
                return re.sub(r'[\s\u3000]+', ' ', val or '').strip()

            for act in root.findall('.//com.dsc.nana.services.webservice.ActInstanceInfo'):
                activity = clean(act.findtext('activityName', default=''))
                state = clean(act.findtext('state', default=''))
                state_display = STATE_DISPLAY.get(state, state)

                for perf in act.findall('.//com.dsc.nana.services.webservice.PerformDetail'):
                    signer = clean(perf.findtext('performerName', default=''))
                    time = clean(perf.findtext('performedTime', default=''))
                    comment = clean(perf.findtext('comment', default=''))

                    history.append({
                        'activity': activity,
                        'state': state_display,
                        'signer': signer,
                        'time': time,
                        'comment': comment,
                    })

            # 只更新歷程，不更新狀態
            self.history_ids = [(5, 0, 0)]
            for row in history:
                self.history_ids = [(0, 0, row)]

            message = f'✅ 已更新簽核歷程 ({len(history)} 筆記錄)'

        except Exception as e:
            self.history_ids = [(5, 0, 0)]
            message = f'❌ 更新歷程失敗: {str(e)}'

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'title': '更新歷程',
                'message': message,
                'sticky': False,
            }
        }

    def action_update_efgp_status(self):
        """只更新 EFGP 狀態（保持原有功能）"""
        for rec in self:
            if not rec.efgp_serial_no:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': '更新 EFGP 狀態失敗',
                        'message': '沒有 EFGP 序號，無法查詢狀態',
                        'sticky': False,
                    }
                }

            try:
                from zeep import Client
                import xml.etree.ElementTree as ET

                wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
                client = Client(wsdl=wsdl)

                # 使用 fetchProcInstanceWithSerialNo 查詢基本狀態
                result_xml = client.service.fetchProcInstanceWithSerialNo(
                    pProcessInstanceSerialNo=rec.efgp_serial_no
                )

                root = ET.fromstring(result_xml)

                process_state = root.findtext('.//state', '').strip()
                process_name = root.findtext('.//processName', '').strip()
                start_time = root.findtext('.//startTime', '').strip()
                end_time = root.findtext('.//endTime', '').strip()

                # 狀態對應表
                STATE_MAPPING = {
                    'open.running.not_performed': 'submitted',
                    'closed.completed': 'approved',
                    'closed.terminated': 'cancelled',
                    'open.running.performed': 'submitted',
                }

                new_state = STATE_MAPPING.get(process_state, rec.state)

                if new_state != rec.state:
                    old_state = rec.state
                    rec.write({'state': new_state})

                    rec.message_post(
                        body=_(
                            '🔄 EFGP 狀態已更新: %s -> %s\n流程狀態: %s\n流程名稱: %s\n開始時間: %s\n結束時間: %s') % (
                                 old_state, new_state, process_state, process_name, start_time, end_time
                             )
                    )

                    message = f'✅ 狀態已更新: {old_state} → {new_state}'
                else:
                    rec.message_post(
                        body=_('ℹ️ EFGP 狀態查詢完成\n流程狀態: %s\n流程名稱: %s\n開始時間: %s\n結束時間: %s') % (
                            process_state, process_name, start_time, end_time
                        )
                    )
                    message = f'ℹ️ 狀態保持不變: {rec.state}'

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'EFGP 狀態更新成功',
                        'message': message,
                        'sticky': False,
                    }
                }

            except Exception as e:
                error_msg = str(e)
                rec.message_post(
                    body=_('❌ EFGP 狀態查詢失敗: %s') % error_msg
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'EFGP 狀態更新失敗',
                        'message': f'查詢失敗: {error_msg}',
                        'sticky': False,
                    }
                }

    def action_update_efgp_status(self):
        """更新EFGP狀態 - 查詢流程基本狀態並更新Odoo狀態"""
        # JI_STAMP/models/stamp_application.py (action_update_efgp_status 方法中)
        for rec in self:
            if not rec.efgp_serial_no:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': '更新EFGP狀態失敗',
                        'message': '沒有EFGP序號，無法查詢狀態',
                        'sticky': False,
                    }
                }

            try:
                from zeep import Client
                import xml.etree.ElementTree as ET
                import re

                # 確保 _logger 變數可用 (假設已在模組頂部定義)
                import logging
                _logger = logging.getLogger(__name__)

                wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
                client = Client(wsdl=wsdl)

                # 使用 fetchProcInstanceWithSerialNo 查詢基本狀態
                result_xml = client.service.fetchProcInstanceWithSerialNo(
                    pProcessInstanceSerialNo=rec.efgp_serial_no
                )

                # 【📌 關鍵新增 1：記錄原始 XML】
                _logger.info("EFGP 狀態查詢原始 XML 回傳:\n%s" % result_xml)

                # 解析XML回應
                root = ET.fromstring(result_xml)

                # 提取狀態資訊
                process_state = root.findtext('.//state', '').strip()

                # 【📌 關鍵新增 2：記錄提取的狀態代碼】
                _logger.info("EFGP 狀態查詢，提取的狀態代碼: %s" % process_state)

                process_name = root.findtext('.//processName', '').strip()
                start_time = root.findtext('.//startTime', '').strip()
                end_time = root.findtext('.//endTime', '').strip()

                # 狀態對應表 (包含所有嘗試的結案代碼)
                STATE_MAPPING = {
                    'open.running.not_performed': 'submitted',  # 審核中 -> 已送簽
                    'closed.completed': 'approved',  # 預設的已完成代碼 -> 已核准
                    'closed.terminated': 'cancelled',  # 已終止 -> 已取消
                    'open.running.performed': 'submitted',  # 執行中 -> 已送簽

                    # 測試的結案代碼
                    'complete': 'approved',
                    'finished': 'approved',
                    'closed': 'approved',
                    'closed.finished': 'approved',
                }

                # 更新Odoo狀態
                new_state = STATE_MAPPING.get(process_state, rec.state)
                if new_state != rec.state:
                    rec.write({'state': new_state})
                    rec.message_post(
                        body=_('🔄 EFGP狀態已更新: %s -> %s\n流程名稱: %s\n開始時間: %s\n結束時間: %s') % (
                            rec.state, new_state, process_name, start_time, end_time
                        )
                    )
                else:
                    rec.message_post(
                        body=_('ℹ️ EFGP狀態查詢完成\n流程狀態: %s\n流程名稱: %s\n開始時間: %s\n結束時間: %s') % (
                            process_state, process_name, start_time, end_time
                        )
                    )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'EFGP狀態更新成功',
                        'message': f'已查詢EFGP狀態: {process_state}\n流程名稱: {process_name}',
                        'sticky': False,
                    }
                }

            except Exception as e:
                error_msg = str(e)
                rec.message_post(
                    body=_('❌ EFGP狀態查詢失敗: %s') % error_msg
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'EFGP狀態更新失敗',
                        'message': f'查詢失敗: {error_msg}',
                        'sticky': False,
                    }
                }
    @api.model
    def get_stamp_history(self, ids):
        import xml.etree.ElementTree as ET
        import re
        res = []
        for rec in self.browse(ids):
            if not rec.efgp_serial_no:
                continue
            wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
            try:
                from zeep import Client
                client = Client(wsdl=wsdl)
                result_xml = client.service.fetchFullProcInstanceWithSerialNo(
                    pProcessInstanceSerialNo=rec.efgp_serial_no)
                root = ET.fromstring(result_xml)

                def clean(val):
                    return re.sub(r'[\s\u3000]+', ' ', val or '').strip()

                for act in root.findall('.//com.dsc.nana.services.webservice.ActInstanceInfo'):
                    activity = clean(act.findtext('activityName', default=''))
                    state = clean(act.findtext('state', default=''))
                    for perf in act.findall('.//com.dsc.nana.services.webservice.PerformDetail'):
                        signer = clean(perf.findtext('performerName', default=''))
                        time = clean(perf.findtext('performedTime', default=''))
                        comment = clean(perf.findtext('comment', default=''))
                        res.append({
                            'activity': activity,
                            'state': state,
                            'signer': signer,
                            'time': time,
                            'comment': comment,
                        })
            except Exception as e:
                res.append({'activity': '查詢失敗', 'state': '', 'signer': '', 'time': '', 'comment': str(e)})
        return res

    def _validate_xml(self, xml_content):
        """驗證 XML 格式是否正確"""
        try:
            import xml.etree.ElementTree as ET
            # 嘗試解析 XML
            ET.fromstring(xml_content)
            return True
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'XML 驗證失敗: {error_msg}')
            _logger.error(f'XML 內容 (前500字元): {xml_content[:500]}')
            return False

    def _generate_attachment_xml(self, rec, pi_oid=None):
        """生成附件 XML，參考正確的 EFGP 格式"""
        import base64
        import html
        import uuid
        import time
        import os

        # 取得 Chatter 附件
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'stamp.application'),
            ('res_id', '=', rec.id)
        ])

        if not attachments:
            return "    <Attachment id=\"Attachment\">\n        <attachments>\n        </attachments>\n    </Attachment>\n"

        attachment_xml = "    <Attachment id=\"Attachment\">\n        <attachments>\n"

        for attachment in attachments:
            try:
                # 取得檔案內容
                file_content = attachment.raw or attachment.datas
                if not file_content:
                    _logger.warning(f'無法取得附件 {attachment.name} 的內容')
                    continue

                # 檢查檔案大小，避免過大的檔案
                if len(file_content) > 10 * 1024 * 1024:  # 10MB
                    _logger.warning(f'附件 {attachment.name} 過大，跳過處理')
                    continue

                # 使用傳入的 PI OID 作為附件 OID，如果沒有則使用隨機 UUID
                import uuid
                oid = pi_oid if pi_oid else str(uuid.uuid4()).replace('-', '')

                # 生成 id 和 name，包含副檔名
                file_extension = ""
                if attachment.name and '.' in attachment.name:
                    file_extension = attachment.name.split('.')[-1]
                elif attachment.mimetype:
                    if 'pdf' in attachment.mimetype:
                        file_extension = 'pdf'
                    elif 'image' in attachment.mimetype:
                        file_extension = 'jpg'
                    elif 'text' in attachment.mimetype:
                        file_extension = 'txt'
                    else:
                        file_extension = 'bin'
                else:
                    file_extension = 'bin'

                # 生成 id 和 name，格式：32位UUID.副檔名（無連字符）
                file_id = str(uuid.uuid4()).replace('-', '') + '.' + file_extension
                file_name = file_id  # id 和 name 相同

                # 處理檔案名稱，使用 html.escape 進行安全轉義
                safe_filename = attachment.name or '附件'
                safe_filename = html.escape(safe_filename, quote=True)

                # 取得檔案類型
                file_type = attachment.mimetype or 'application/octet-stream'
                if '/' in file_type:
                    file_type = file_type.split('/')[-1]

                # 取得檔案大小
                file_size = len(file_content)

                # 取得上傳時間（毫秒）
                upload_time = int(time.time() * 1000)

                # 取得創建者資訊
                creator_oid = "1510da25f51510048c78e2dd31f1da3d"  # 預設值
                creator_name = rec.applicant_id.name or 'admin'
                safe_creator_name = html.escape(creator_name, quote=True)

                # 生成附件 XML，參考正確的 EFGP 格式
                attachment_xml += f"""            <attachment OID=\"{oid}\" id=\"{file_id}\" name=\"{file_name}\" originalFileName=\"{safe_filename}\" fileType=\"{file_type}\" fileSize=\"{file_size}\" uploadTime=\"{upload_time}\" creatorOID=\"{creator_oid}\" creatorName=\"{safe_creator_name}\" activityName=\"用印申請\" onlineRead=\"0\" isConvertPDF=\"1\">
                <description></description>
                <permission>
                    <user OID=\"{creator_oid}\" restriction=\"1\"></user>
                </permission>
            </attachment>\n"""

                _logger.info(f'成功處理附件 XML: {attachment.name}, 大小: {file_size} bytes, OID: {oid}, id: {file_id}')

            except Exception as e:
                _logger.error(f'處理附件 {attachment.name} 時發生錯誤: {str(e)}')
                continue

        attachment_xml += "        </attachments>\n    </Attachment>\n"
        return attachment_xml

    def test_attachment_xml_generation(self):
        """測試附件 XML 生成功能"""
        for rec in self:
            try:
                # 生成附件 XML
                attachment_xml = self._generate_attachment_xml(rec, None)

                # 記錄到 Chatter
                rec.message_post(
                    body=_('📎 附件 XML 測試結果 (新格式):\n%s') % attachment_xml
                )

                _logger.info(f'附件 XML 生成成功，長度: {len(attachment_xml)} 字元')

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': '附件 XML 測試完成',
                        'message': f'附件 XML 已生成並記錄到 Chatter，長度: {len(attachment_xml)} 字元',
                        'sticky': False,
                    }
                }

            except Exception as e:
                error_msg = str(e)
                _logger.error(f'附件 XML 測試失敗: {error_msg}')

                rec.message_post(
                    body=_('❌ 附件 XML 測試失敗:\n%s') % error_msg
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': '附件 XML 測試失敗',
                        'message': f'附件 XML 測試失敗: {error_msg}',
                        'sticky': False,
                    }
                }

    def debug_xml_content(self):
        """調試 XML 內容，查看生成的 XML"""
        for rec in self:
            try:
                # 生成附件 XML
                attachment_xml = self._generate_attachment_xml(rec, None)

                # 生成表單 XML（模擬送簽過程）
                from zeep import Client
                import xml.etree.ElementTree as ET

                wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
                client = Client(wsdl=wsdl)
                process_id = "stamp"

                # 1. 取得表單 OID
                form_oid_xml = client.service.findFormOIDsOfProcess(pProcessPackageId=process_id)
                form_oid = form_oid_xml.strip()

                # 2. 取得表單欄位結構
                form_field_xml = client.service.getFormFieldTemplate(pFormDefinitionOID=form_oid)
                form_root = ET.fromstring(form_field_xml)

                # 3. 設定欄位內容
                for field in form_root.iter():
                    fid = field.attrib.get('id')
                    if fid == 'SerialNumber1':
                        field.text = rec.efgp_serial_no or ""
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                    elif fid == 'itemno':
                        field.text = rec.name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'Date4':
                        field.text = rec.date.strftime('%Y/%m/%d') if rec.date else ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.util.Date'
                        if 'list_hidden' not in field.attrib:
                            field.attrib['list_hidden'] = ''
                    elif fid == 'odoouser':
                        field.text = rec.applicant_id.name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'subject':
                        field.text = rec.document_name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'note':
                        field.text = rec.description or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''

                final_xml = ET.tostring(form_root, encoding='unicode')

                # 4. 加入附件 XML
                if "<attachment OID=" in attachment_xml:
                    # 有附件，需要正確組合 XML 結構
                    if final_xml.endswith('</stamp>'):
                        final_xml = final_xml[:-8]  # 移除 </stamp>
                        # 加入附件 XML 和結尾標籤
                        final_xml = final_xml + '\n' + attachment_xml + '\n</stamp>'
                    else:
                        # 如果沒有 </stamp> 結尾，直接加入
                        final_xml = final_xml + '\n' + attachment_xml

                # 記錄到 Chatter
                debug_info = f"""
📋 XML 調試資訊:

🔹 附件 XML:
{attachment_xml}

🔹 完整 XML (前500字元):
{final_xml[:500]}...

🔹 XML 長度: {len(final_xml)} 字元
🔹 附件數量: {len(rec.attachment_ids)} 個
🔹 XML 驗證: {'✅ 通過' if self._validate_xml(final_xml) else '❌ 失敗'}
"""

                rec.message_post(
                    body=_(debug_info)
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'XML 調試完成',
                        'message': f'XML 調試資訊已記錄到 Chatter，XML 長度: {len(final_xml)} 字元',
                        'sticky': False,
                    }
                }

            except Exception as e:
                error_msg = str(e)
                _logger.error(f'XML 調試失敗: {error_msg}')

                rec.message_post(
                    body=_('❌ XML 調試失敗:\n%s') % error_msg
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'XML 調試失敗',
                        'message': f'XML 調試失敗: {error_msg}',
                        'sticky': False,
                    }
                }

    def debug_submit_xml(self):
        """調試送簽 XML 內容"""
        for rec in self:
            try:
                # 模擬送簽過程的 XML 生成
                from zeep import Client
                import xml.etree.ElementTree as ET

                wsdl = "http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl"
                client = Client(wsdl=wsdl)
                process_id = "stamp"

                # 1. 取得表單 OID
                form_oid_xml = client.service.findFormOIDsOfProcess(pProcessPackageId=process_id)
                form_oid = form_oid_xml.strip()

                # 2. 取得表單欄位結構
                form_field_xml = client.service.getFormFieldTemplate(pFormDefinitionOID=form_oid)
                form_root = ET.fromstring(form_field_xml)

                # 3. 設定欄位內容
                for field in form_root.iter():
                    fid = field.attrib.get('id')
                    if fid == 'SerialNumber1':
                        field.text = rec.efgp_serial_no or ""
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                    elif fid == 'itemno':
                        field.text = rec.name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'Date4':
                        field.text = rec.date.strftime('%Y/%m/%d') if rec.date else ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.util.Date'
                        if 'list_hidden' not in field.attrib:
                            field.attrib['list_hidden'] = ''
                    elif fid == 'odoouser':
                        field.text = rec.applicant_id.name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'subject':
                        field.text = rec.document_name or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''
                    elif fid == 'note':
                        field.text = rec.description or ''
                        if 'dataType' not in field.attrib:
                            field.attrib['dataType'] = 'java.lang.String'
                        if 'perDataProId' not in field.attrib:
                            field.attrib['perDataProId'] = ''

                # 4. 生成附件 XML
                attachment_xml = self._generate_attachment_xml(rec, None)

                # 5. 組合最終 XML
                final_xml = ET.tostring(form_root, encoding='unicode')
                if "<attachment OID=" in attachment_xml:
                    # 有附件，需要正確組合 XML 結構
                    if final_xml.endswith('</stamp>'):
                        final_xml = final_xml[:-8]  # 移除 </stamp>
                        # 加入附件 XML 和結尾標籤
                        final_xml = final_xml + '\n' + attachment_xml + '\n</stamp>'
                    else:
                        # 如果沒有 </stamp> 結尾，直接加入
                        final_xml = final_xml + '\n' + attachment_xml

                # 6. 驗證 XML
                xml_valid = self._validate_xml(final_xml)

                # 記錄到 Chatter
                debug_info = f"""
🔍 送簽 XML 調試資訊:

📋 附件 XML:
{attachment_xml}

📋 完整 XML (前2000字元):
{final_xml[:2000]}

📊 統計資訊:
• XML 長度: {len(final_xml)} 字元
• 附件數量: {len(rec.attachment_ids)} 個
• XML 驗證: {'✅ 通過' if xml_valid else '❌ 失敗'}
• 附件 XML 長度: {len(attachment_xml)} 字元
"""

                rec.message_post(
                    body=_(debug_info)
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'XML 調試完成',
                        'message': f'XML 調試資訊已記錄到 Chatter，XML 長度: {len(final_xml)} 字元，驗證: {"通過" if xml_valid else "失敗"}',
                        'sticky': False,
                    }
                }

            except Exception as e:
                error_msg = str(e)
                _logger.error(f'XML 調試失敗: {error_msg}')

                rec.message_post(
                    body=_('❌ XML 調試失敗:\n%s') % error_msg
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {
                        'title': 'XML 調試失敗',
                        'message': f'XML 調試失敗: {error_msg}',
                        'sticky': False,
                    }
                }