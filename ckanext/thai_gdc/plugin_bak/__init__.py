# encoding: utf-8
import os, sys, json, logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


if tk.check_ckan_version(u'2.9'):
    from ckanext.thai_gdc.plugin.flask_plugin import MixinPlugin
else:
    from ckanext.thai_gdc.plugin.pylons_plugin import MixinPlugin


class Thai_GDCPlugin(MixinPlugin, plugins.SingletonPlugin, DefaultTranslation, toolkit.DefaultDatasetForm):