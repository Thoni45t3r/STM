# -*- coding: utf-8 -*-

{
    'name': 'Table header freeze',
    'version': '1.0',
    'sequence': 33,
    'category': 'Extra Tools',
    #'website': 'http://manangewall.mn',
    'author': 'InceptionMara',
    'price': 15.0,
    'license':'LGPL-3',
    'currency': 'USD',
    'description': """
        - Easy use
        - Tree view header freeze
        - One2many tree view header freeze """,
    'images': [
        'static/description/icon.jpg',
    ],
    'depends': ['base'],
    'summary': '',
    'data': [
        'views/widget_path.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': ['static/xml/*.xml'],
}
