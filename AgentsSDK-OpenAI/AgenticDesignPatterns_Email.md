# AgenticDesignPatterns_Email.py

Demostración práctica de **patrones de diseño agéntico** (*Agentic Design Patterns*) aplicados a la generación y envío automatizado de emails de ventas en frío, utilizando el **OpenAI Agents SDK** y **SendGrid** como proveedor de correo.

---

## ¿Qué hace el programa?

El script implementa un sistema multi-agente que genera, evalúa y envía emails de ventas en frío para la empresa ficticia **ComplAI** (SaaS de compliance SOC2). El flujo completo se divide en cuatro demostraciones que ilustran distintos patrones:

| # | Demostración | Patrón |
|---|---|---|
| 1 | `demo_streamed_email` | Streaming de un solo agente |
| 2 | `demo_parallel_and_pick_best` | Ejecución paralela + selección del mejor |
| 3 | `demo_sales_manager_simple` | Manager con herramientas (*tool-use orchestration*) |
| 4 | `demo_sales_manager_with_handoff` | Manager con *handoff* a agente especializado |

### Agentes involucrados

| Agente | Rol |
|---|---|
| **Professional Sales Agent** | Genera borradores con tono profesional y serio |
| **Engaging Sales Agent** | Genera borradores con tono cercano y humorístico |
| **Busy Sales Agent** | Genera borradores concisos y directos |
| **sales_picker** | Evalúa y elige el mejor borrador |
| **Email subject writer** | Redacta el asunto del email |
| **HTML email body converter** | Convierte el cuerpo de texto a HTML |
| **Email Manager** | Orquesta el formateo (asunto + HTML) y el envío |
| **Sales Manager** | Orquesta a los agentes de ventas y decide qué enviar |

---

## Patrones de diseño agéntico implementados

### 1. Streaming de un solo agente
El agente genera texto y los tokens se imprimen en tiempo real usando `Runner.run_streamed`. Útil para dar feedback visual inmediato al usuario.

### 2. Paralelización + selección del mejor resultado
Los tres agentes de ventas se ejecutan **en paralelo** con `asyncio.gather`, reduciendo la latencia total. Un agente *picker* evalúa los tres borradores y selecciona el más efectivo.

### 3. Manager con herramientas (*Tool-use Orchestration*)
El **Sales Manager** llama a los agentes de ventas como **herramientas** (tools), elige el mejor borrador y lo envía directamente como texto plano usando `send_email`.

### 4. Manager con *Handoff*
El **Sales Manager** genera y evalúa borradores, luego hace un **handoff** (delegación de control) al **Email Manager**. Este agente especializado se encarga de:
1. Generar un asunto atractivo (`subject_writer` tool)
2. Convertir el cuerpo a HTML (`html_converter` tool)
3. Enviar el email formateado (`send_html_email` tool)

---

## Temas cubiertos

- **OpenAI Agents SDK**: `Agent`, `Runner`, `trace`, `function_tool`
- **Herramientas de agente** (`as_tool`): convertir un agente en una tool callable por otro agente
- **Handoffs**: delegación de control entre agentes especializados
- **Streaming de LLMs**: lectura de eventos en tiempo real con `run_streamed`
- **Paralelización de agentes**: `asyncio.gather` para ejecutar múltiples agentes simultáneamente
- **Trazabilidad**: uso de `trace` para seguimiento de ejecuciones en OpenAI
- **Integración con SendGrid**: envío de emails de texto plano y HTML mediante la API REST
- **Gestión segura de secretos**: uso de `python-dotenv` y variables de entorno para credenciales

---

## Lo que se aprendió

- Cómo estructurar sistemas multi-agente usando el SDK de OpenAI Agents.
- La diferencia práctica entre el patrón **tool-use** (el manager mantiene el control y llama sub-agentes como herramientas) y el patrón **handoff** (el manager transfiere el control completo a otro agente).
- Que `asyncio.gather` permite reducir significativamente la latencia cuando se lanzan múltiples agentes que no dependen entre sí.
- La importancia de **no hardcodear credenciales** (emails, API keys) directamente en el código; siempre deben leerse desde variables de entorno.
- Cómo exponer un agente como herramienta (`agent.as_tool(...)`) para que pueda ser invocado por otro agente dentro de su loop de razonamiento.
- Que el streaming (`run_streamed`) mejora la experiencia de usuario al mostrar respuestas incrementales en lugar de esperar la respuesta completa.

---

## Requisitos

- Python 3.10+
- Cuenta en [OpenAI](https://platform.openai.com/) con acceso a la API
- Cuenta en [SendGrid](https://sendgrid.com/) con una dirección de remitente verificada

### Dependencias

```
openai-agents
sendgrid
python-dotenv
```

Instalar con:

```bash
pip install openai-agents sendgrid python-dotenv
```

---

## Configuración

Crear un archivo `.env` en la raíz del proyecto (o en el directorio `AgentsSDK-OpenAI/`) con las siguientes variables:

```env
OPENAI_API_KEY=sk-...            # API key de OpenAI
SENDGRID_API_KEY=SG...           # API key de SendGrid
EMAIL_FROM=tu_email@dominio.com  # Remitente verificado en SendGrid
EMAIL_TO=destinatario@dominio.com # Destinatario de los emails de prueba/ventas
```

> ⚠️ **Nunca** subas el archivo `.env` al repositorio. Asegúrate de que esté en tu `.gitignore`.

---

## Cómo ejecutar

```bash
cd AgentsSDK-OpenAI
python AgenticDesignPatterns_Email.py
```

El script ejecutará las cuatro demostraciones de forma secuencial e imprimirá el resultado de cada una por consola.

---

## Seguridad

- Las credenciales (`SENDGRID_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`) se gestionan exclusivamente mediante variables de entorno, nunca se hardcodean en el código.
- El programa valida al inicio de cada función de envío que las variables requeridas estén definidas, fallando de forma explícita con un mensaje descriptivo si no es así.
- El archivo `.env` **no debe** incluirse en el control de versiones.
