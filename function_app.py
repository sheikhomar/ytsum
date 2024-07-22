import azure.functions as func
from ytsum import say_hello

app = func.FunctionApp()


@app.function_name(name="hello")
@app.route(route="main/hello", auth_level=func.AuthLevel.ANONYMOUS)
def main(req: func.HttpRequest) -> func.HttpResponse:
    output = say_hello()
    return func.HttpResponse(body=output, status_code=200)
