# Caché, seguridad y evaluación de calidad

Cambios del 4 de noviembre de 2026, posteriores al bloque de importación y
pruebas seguras. Conservan las rutas API, los formatos de respuesta y las
reglas agrícolas. No se modificó ni publicó configuración del entorno.

## Caché de cuarentena

La clave incluye página, tamaño, tabla y estado como una tupla JSON. Distingue
ausencia de filtro y textos literales, evitando colisiones por delimitadores.
El formato nuevo no reutiliza entradas antiguas sin estado; estas expiran con
su TTL. Se conserva la invalidación por prefijo `cuarentena:`.

## Autorización vigente

El JWT sigue validando firma y expiración. La lectura de usuario activo que ya
existía proporciona ahora el rol y el nombre vigentes. Una degradación de admin
a viewer impide usar endpoints de admin con el token anterior; una elevación
se refleja con la misma política. Roles desconocidos no otorgan permisos.
Usuario inexistente/inactivo y tokens inválidos o expirados conservan HTTP 401.
No se agregó otra consulta ni otro estado de sesión.

## Logs del backend

- Los errores de validación registran ubicación y tipo, omitiendo input, ctx
  y mensajes de validadores; la respuesta HTTP conserva su contrato.
- El sanitizador procesa mensajes y campos adicionales anidados. Redacta
  campos identificados como credenciales/inputs/PII, asignaciones de credenciales
  y Bearer en texto, y mantiene el enmascaramiento de DNI/RUC.
- Las excepciones conservan tipo y ubicaciones de la pila. Sus mensajes,
  parámetros, variables locales y líneas de código fuente se omiten porque
  pueden contener valores sensibles. Objetos opacos en extras se representan
  por su tipo en lugar de volcar su repr. Los emisores deben seguir evitando
  incluir secretos arbitrarios en texto libre.
- El request ID vive en un ContextVar con restauración mediante token. Se
  propaga a tareas/hilos delegados y se restaura también ante errores.
- Correlación y saneamiento se instalan en handlers raíz, incluidos los
  preexistentes, para cubrir registros de loggers hijos. Configurar logging
  repetidamente no duplica esos filtros.

## Circuit breaker

`BaseFactProcessor.finalizar_proceso` usa `utils.circuit_breaker.evaluar` con
los umbrales de la instancia. Se retiró la evaluación inline duplicada y los
defaults del procesador apuntan a las constantes canónicas. El método pasó de
114 a 77 líneas físicas; esta medida no equivale a complejidad cognitiva.

Se mantienen la muestra mínima de 50, los umbrales especiales por fact,
el conteo de IDs únicos rechazados, la exclusión de duplicados técnicos y la
detección de pérdida silenciosa. También se conserva el campo legado
`Bloqueo_Integridad` y la ausencia de mensaje de bloqueo cuando no hay nivel.
Los textos diagnósticos de bloqueo proceden ahora del evaluador canónico.

La evaluación devuelve un dictamen. En incremental, el orquestador decide
después del commit de carga; en reconstrucción atómica, un ERROR/CRITICO revierte
la transacción externa. Esta entrega no cambia la política de muestras pequeñas
ni añade nuevos motivos de rechazo.

## Verificación

Las nuevas regresiones de caché y seguridad reprodujeron primero 12 fallos;
los cuatro casos de rechazo de sesiones inválidas ya pasaban. Las pruebas de
caracterización del procesador pasaron antes de sustituir la evaluación.
Se reemplazaron comprobaciones de texto fuente/payloads fabricados del breaker
por llamadas a producción, límites, duplicados y subclases reales.

Comando desde la raíz:

```bash
python -m pytest -q
```

Resultado: **194 aprobadas, 9 omitidas**, sin fallos. Las nueve omitidas son
integración SQL Server. Incluye HTTP con JWT real y repositorio sustituido,
caché SQLite temporal real, logs JSON/texto, concurrencia/to_thread y transacciones
SQLite reales para comprobar commit incremental y rollback de reconstrucción
en niveles ERROR y CRITICO. No demuestra el comportamiento del driver SQL Server.

No se incorporaron dependencias. Cobertura porcentual y rendimiento no medidos.
Estado: **APROBADO para el alcance local verificado**. Integración SQL Server
pendiente; se mantiene la decisión de trabajar sin base de datos remota.
