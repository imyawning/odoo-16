# -*- coding: utf-8 -*-
{
    'name': 'DSC材料物性測試報告',
    'version': '1.0',
    'category': 'Manufacturing',
    # ... 其他欄位 ...
    'depends': ['base', 'product', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',

        # === Reports 必須在 Views 之前 ===
        'report/test_report_template.xml',
        'report/test_report.xml',

        # === Views ===
        'views/test_config_views.xml',
        'views/test_template_views.xml',
        'views/test_report_views.xml',  # 引用 ID 的檔案在後面

        'views/menus.xml',
    ],
}