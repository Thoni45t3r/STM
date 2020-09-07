Table header freeze
================================

This module Table header freeze your odoo module in tree view 

Features
========

* Your choosen in tree view
* Main tree view freeze
* One2many field's in tree view

Usage
=====

You need to declare in *.xml file:
In the view declaration, put class='table_header_freeze' attribute in the field tag::
	1. Main tree view:

    <record model='ir.ui.view' id='technic_tire_tree'>
        <field name="name">Technic tire tree</field>
        <field name="model">technic.tire</field>
        <field name="arch" type="xml">
            <tree class="table_header_freeze">
                <field name="date_of_record" invisible="1"/>
                <field name="brand_id"/>
                <field name="user_id"/>
            </tree>
        </field>
    </record>

    2. In the One2many field's tree view

    <field name="tire_depreciation_lines" nolabel="1" colspan="4">
	    <tree string="Depreciation history" editable="bottom"
	        class="table_header_freeze">
	        <field name="date"/>
	        <field name="technic_id" invisible="1"/>
	        <field name="increasing_odometer" sum="Нийт"/>
	        <field name="increasing_km" sum="Нийт"/>
	        <field name="depreciation_percent"/>
	        <field name="depreciation_amount" sum="Элэгдсэн дүн"/>
	    </tree>
	</field> 
