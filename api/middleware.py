"""
Middleware para la inyección de metadatos de autoría en las respuestas HTTP.
Intercepta todas las peticiones y añade cabeceras personalizadas.
"""
class FooterMetadataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesamiento normal de la petición
        response = self.get_response(request)
        
        # Inyección de metadatos del desarrollador en las cabeceras (Headers)
        response['X-Student-Name'] = 'Maximo Agusto Aldea Garrido'
        response['X-Student-Section'] = 'IEC-N4-C1'
        response['X-Student-Year'] = '2 año'
        
        return response
