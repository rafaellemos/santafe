#ifndef PIERROR_H
#define PIERROR_H
/*=========================================================================*\
* Error messages
* Defines platform independent error messages
\*=========================================================================*/

#define PIE_HOST_NOT_FOUND "hospedeiro n\xC3\xA3o encontrado"
#define PIE_ADDRINUSE      "endere\xC3\xA7o j\xC3\xA1 est\xC3\xA1 em uso"
#define PIE_ISCONN         "j\xC3\xA1 conectada"
#define PIE_ACCESS         "permiss\xC3\xA3o negada"
#define PIE_CONNREFUSED    "conex\xC3\xA3o recusada"
#define PIE_CONNABORTED    "fechada"
#define PIE_CONNRESET      "fechada"
#define PIE_TIMEDOUT       "tempoEsgotado"
#define PIE_AGAIN          "falha tempor\xC3\xA1ria na resolu\xC3\xA7\xC3\xA3o de nome"
#define PIE_BADFLAGS       "valor inv\xC3\xA1lido para ai_flags"
#define PIE_BADHINTS       "valor inv\xC3\xA1lido para dicas"
#define PIE_FAIL           "falha irrecuper\xC3\xA1vel na resolu\xC3\xA7\xC3\xA3o de nome"
#define PIE_FAMILY         "ai_family n\xC3\xA3o aceita"
#define PIE_MEMORY         "falha na aloca\xC3\xA7\xC3\xA3o de mem\xC3\xB3ria"
#define PIE_NONAME         "hospedeiro ou servi\xC3\xA7o n\xC3\xA3o fornecido ou desconhecido"
#define PIE_OVERFLOW       "estouro do memint de argumentos"
#define PIE_PROTOCOL       "o protocolo resolvido \xC3\xA9 desconhecido"
#define PIE_SERVICE        "servi\xC3\xA7o n\xC3\xA3o aceito para o tipo de tomada"
#define PIE_SOCKTYPE       "ai_socktype n\xC3\xA3o aceito"

#endif
