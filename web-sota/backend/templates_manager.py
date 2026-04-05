from pathlib import Path

from fastapi.templating import Jinja2Templates

from ..config import WebUISettings, get_model


def get_templates():
    web_config = get_model(WebUISettings)
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    templates.env.globals.update(
        {
            "app_title": web_config.title,
            "app_version": "1.0.0",
            "theme": web_config.theme,
        }
    )
    return templates


templates = get_templates()
