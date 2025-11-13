# 錯誤
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    # 這裡可以添加您需要客製化的欄位
    # 例如：
    # asset_category_id = fields.Many2one('asset.category', string='關聯資產類別')
    pass