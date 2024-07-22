import azure.functions as func
from ytsum import say_hello

app = func.FunctionApp()


@app.function_name(name="HttpTrigger1")
@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
def main(req: func.HttpRequest) -> func.HttpResponse:
    output = "No calls to ytsum package."
    output = say_hello()
    return func.HttpResponse(body=output, status_code=200)
