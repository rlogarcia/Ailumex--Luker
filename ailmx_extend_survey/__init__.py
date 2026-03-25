# Cargar la carpeta models

from . import models
from .models import menu_setup
post_init_hook = menu_setup.post_init_hook