"""
El 'Middleware' es un código que funciona como una "aduana". 
Se ejecuta siempre que entra una petición al servidor o cuando sale una respuesta.
"""
class FooterMetadataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Primero dejamos que el servidor procese la petición de forma normal
        response = self.get_response(request)
        
        # Una vez que tenemos la respuesta, le "inyectamos" tus datos como estudiante
        # de forma permanente. Esto aparecerá en las cabeceras (Headers) de todas las respuestas.
        response['X-Student-Name'] = 'Maximo Agusto Aldea Garrido'
        response['X-Student-Section'] = 'IEC-N4-C1'
        response['X-Student-Year'] = '2 año'
        
        return response
