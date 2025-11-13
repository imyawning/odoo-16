# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

# 第一層：繼承 Odoo 標準模型（無依賴）
from . import account_move
from . import product_category

# 第二層：基礎配置模型（無相互依賴）
from . import asset_config
from . import asset_category

# 第三層：主要業務模型
from . import asset_master

# 第四層：依賴主要模型的業務邏輯
from . import asset_depreciation
from . import asset_disposal
from . import asset_adjust
from . import asset_sale

# 第五層：精靈和報表
from . import asset_exe_depreciation_wizard
from . import asset_reverse_depreciation_wizard
from . import asset_depreciation_report
from . import asset_master_report