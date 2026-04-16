# -*- coding: utf-8 -*-


def post_init_hook(env):
    """
    No se requiere lógica de renombrado.
    Los menús personalizados se gestionan por XML.
    """
    return True


def post_migrate(env, version_from, version_to):
    """
    No se requiere lógica de renombrado.
    Los menús personalizados se gestionan por XML.
    """
    return True