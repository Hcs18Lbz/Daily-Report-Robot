"""Web 管理界面入口: Flask app + 路由。

启动: python -m src.webapp.app
访问: http://127.0.0.1:5000/  (localhost only, 无鉴权)
"""

import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from src.webapp import config_io
from src.webapp.runner import ConflictError, manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(_TEMPLATE_DIR), static_folder=str(_STATIC_DIR))
    app.config["JSON_AS_ASCII"] = False

    @app.context_processor
    def inject_now():
        return {"now": datetime.now()}

    config_io.ensure_tasks()

    @app.route("/")
    def dashboard():
        feeds = config_io.read_rss_feeds()
        schedule = config_io.read_schedule()
        next_runs = config_io.get_next_run_times()
        recent = manager.list_history(limit=5)
        webhook_set = bool(config_io.read_env("FEISHU_WEBHOOK_URL").strip()) and "YOUR_WEBHOOK" not in config_io.read_env("FEISHU_WEBHOOK_URL")
        api_key_set = bool(config_io.read_env("NVIDIA_API_KEY").strip())
        return render_template(
            "dashboard.html",
            feeds=feeds,
            schedule=schedule,
            next_runs=next_runs,
            recent=recent,
            webhook_set=webhook_set,
            api_key_set=api_key_set,
        )

    @app.route("/feeds")
    def feeds_list():
        return render_template("feeds.html", feeds=config_io.read_rss_feeds(), form=None, edit_idx=None, error=None)

    @app.route("/feeds/new", methods=["GET"])
    def feeds_new():
        return render_template("feeds.html", feeds=config_io.read_rss_feeds(), form={"name": "", "url": ""}, edit_idx=-1, error=None)

    @app.route("/feeds/<int:idx>/edit", methods=["GET"])
    def feeds_edit(idx: int):
        feeds = config_io.read_rss_feeds()
        if idx < 0 or idx >= len(feeds):
            abort(404)
        return render_template("feeds.html", feeds=feeds, form=feeds[idx], edit_idx=idx, error=None)

    @app.route("/feeds/save", methods=["POST"])
    def feeds_save():
        edit_idx = int(request.form.get("edit_idx", "-1"))
        new_feed = {
            "name": request.form.get("name", ""),
            "url": request.form.get("url", ""),
        }
        feeds = config_io.read_rss_feeds()
        if edit_idx == -1:
            feeds.append(new_feed)
        else:
            if edit_idx < 0 or edit_idx >= len(feeds):
                abort(404)
            feeds[edit_idx] = new_feed
        try:
            config_io.write_rss_feeds(feeds)
        except config_io.ValidationError as e:
            return render_template("feeds.html", feeds=config_io.read_rss_feeds(), form=new_feed, edit_idx=edit_idx, error=str(e))
        return redirect(url_for("feeds_list"))

    @app.route("/feeds/<int:idx>/delete", methods=["POST"])
    def feeds_delete(idx: int):
        feeds = config_io.read_rss_feeds()
        if idx < 0 or idx >= len(feeds):
            abort(404)
        feeds.pop(idx)
        try:
            config_io.write_rss_feeds(feeds)
        except config_io.ValidationError as e:
            return render_template("feeds.html", feeds=config_io.read_rss_feeds(), form=None, edit_idx=None, error=str(e))
        return redirect(url_for("feeds_list"))

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        if request.method == "POST":
            return _save_settings()
        return _render_settings(error=None)

    def _save_settings():
        webhook = request.form.get("webhook_url", "").strip()
        api_key = request.form.get("nvidia_api_key", "")
        morning = request.form.get("morning", "").strip()
        evening = request.form.get("evening", "").strip()

        errors: list[str] = []
        try:
            config_io.write_env("FEISHU_WEBHOOK_URL", webhook)
        except OSError as e:
            errors.append(f"写 Webhook 失败: {e}")
        if api_key:
            try:
                config_io.write_env("NVIDIA_API_KEY", api_key)
            except OSError as e:
                errors.append(f"写 API Key 失败: {e}")
        if not errors:
            try:
                config_io.write_schedule(morning, evening)
            except (config_io.ValidationError, config_io.ScheduleError) as e:
                errors.append(str(e))

        if errors:
            return _render_settings(error=" / ".join(errors))
        return redirect(url_for("settings"))

    def _render_settings(error: str | None):
        webhook = config_io.read_env("FEISHU_WEBHOOK_URL")
        api_key_set = bool(config_io.read_env("NVIDIA_API_KEY"))
        schedule = config_io.read_schedule()
        return render_template(
            "settings.html",
            webhook=webhook,
            api_key_set=api_key_set,
            schedule=schedule,
            error=error,
        )

    @app.route("/run", methods=["POST"])
    def run_trigger():
        try:
            run_id = manager.trigger()
        except ConflictError as e:
            return jsonify({"error": str(e)}), 409
        return jsonify({"run_id": run_id, "status": "queued"})

    @app.route("/run/<run_id>")
    def run_detail(run_id: str):
        state = manager.get_run_detail(run_id)
        if state is None:
            abort(404)
        return render_template("run.html", state=state, run_id=run_id)

    @app.route("/run/<run_id>/status")
    def run_status(run_id: str):
        state = manager.get_status(run_id)
        if state is None:
            abort(404)
        return jsonify(state)

    @app.route("/history")
    def history_list():
        runs = manager.list_history(limit=50)
        return render_template("history.html", runs=runs)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
