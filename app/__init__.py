from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

import re
from markupsafe import Markup, escape


db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from app import models

    from app.routes import main
    app.register_blueprint(main)

    from app.auth.routes import auth
    app.register_blueprint(auth)

    @app.template_filter("render_question_text")
    def render_question_text(text):
        if not text:
            return ""

        escaped_text = escape(text)

        pattern = re.compile(
            r"```([a-zA-Z0-9]*)\n(.*?)```",
            re.DOTALL
        )

        def replace_code_block(match):
            language = match.group(1) or "code"
            code = match.group(2)

            escaped_language = escape(language)
            escaped_code = escape(code)

            return Markup(
                f"""
                <div class="tapa-code-block">
                    <div class="tapa-code-header">
                        <span>{escaped_language}</span>
                    </div>
                    <pre><code>{escaped_code}</code></pre>
                </div>
                """
            )

        rendered = pattern.sub(replace_code_block, str(escaped_text))
        rendered = rendered.replace("\n", "<br>")

        return Markup(rendered)

    return app