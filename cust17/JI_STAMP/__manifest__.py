{
    'name': 'JI STAMP - 用印申請管理',
    'version': '17.0.1.0',
    'category': 'Human Resources',
    'description': '用印申請單管理系統，整合 EFGP 簽核流程',
    'summary': '用印申請單管理與 EFGP 簽核整合',
    'author': 'JI',
    'license': 'Other proprietary',
    'company': 'JI',
    'maintainer': '',
    'support': '',
    'website': '',
    'depends': ['base', 'mail', 'web'],
    'external_dependencies': {
        'python': ['requests', 'zeep'],
    },
    'data': [
        'data/stamp_config_data.xml',
        'data/stamp_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/stamp_application_views.xml',
        'views/stamp_config_views.xml',
        'views/menu_views.xml',
        'views/stamp_history_qweb.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'JI_STAMP/static/src/css/stamp_application.css',
        ],
    },
} 