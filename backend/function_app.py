import azure.functions as func

from classification.function import main as classification_main
from log_writer.function import main as log_writer_main
from log_ingest_consumer.function import main as log_ingest_consumer_main
from anomaly_checker.function import main as anomaly_checker_main
from api.audit_log import main as audit_log_main
from api.user_stats import main as user_stats_main
from api.policy_config import main as policy_config_main
from teams_notifier.function import main as teams_notifier_main

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="classification", methods=["POST"])
def classification(req: func.HttpRequest) -> func.HttpResponse:
    return classification_main(req)


@app.route(route="log_writer", methods=["POST"])
def log_writer(req: func.HttpRequest) -> func.HttpResponse:
    return log_writer_main(req)


@app.event_hub_message_trigger(
    arg_name="event",
    event_hub_name="eh-audit-events",
    connection="AZURE_EVENT_HUB_CONNECTION_STRING",
)
def log_ingest_consumer(event: func.EventHubEvent):
    log_ingest_consumer_main(event)


@app.route(route="audit_log", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def audit_log(req: func.HttpRequest) -> func.HttpResponse:
    return audit_log_main(req)


@app.route(route="user_stats", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def user_stats(req: func.HttpRequest) -> func.HttpResponse:
    return user_stats_main(req)


@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def anomaly_checker(timer: func.TimerRequest) -> None:
    anomaly_checker_main(timer)


@app.route(route="policy_config", methods=["GET", "PUT"], auth_level=func.AuthLevel.ANONYMOUS)
def policy_config(req: func.HttpRequest) -> func.HttpResponse:
    return policy_config_main(req)


@app.event_grid_trigger(arg_name="event")
def teams_notifier(event: func.EventGridEvent) -> None:
    teams_notifier_main(event)
