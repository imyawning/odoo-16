# -*- coding: utf-8 -*-
{
    'name': 'DSC材料物性測試報告',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'DSC Material Product Test Report Management',
    'description': """
        DSC Material Product Test Report
        ================================
        Manage material testing reports including:
        - Hardness testing
        - Tensile strength
        - Elongation ratio
        - Tear strength
        - Resiliency
        - Specific gravity
        - Shrinkage
        - Compression set
        - Split tear
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'product', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/material_test_report_views.xml',
        'report/material_test_report.xml',
        'report/material_test_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}