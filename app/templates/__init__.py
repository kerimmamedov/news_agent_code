from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml']),
)



def render_html_newsletter(user, articles):
    template = _env.get_template('daily_news_email.html')
    return template.render(user=user, articles=articles)



def render_text_newsletter(user, articles):
    template = _env.get_template('daily_news_email.txt')
    return template.render(user=user, articles=articles)
