import azure.functions as func

from classification.function import main as classification_main
from log_writer.function import main as log_writer_main
from log_ingest_consumer.function import main as log_ingest_consumer_main

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
