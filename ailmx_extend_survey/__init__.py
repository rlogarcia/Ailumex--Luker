# Cargar la carpeta models

from . import models
from . import controllers
from .models import menu_setup
post_init_hook = menu_setup.post_init_hook