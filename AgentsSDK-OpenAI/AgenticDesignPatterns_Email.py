"""
AgenticDesignPatterns_Email.py
==============================
Demostración de patrones de diseño agéntico (Agentic Design Patterns) aplicados
a la generación y envío automatizado de emails de ventas en frío usando:
  - OpenAI Agents SDK
  - SendGrid como proveedor de envío de emails

Patrones implementados:
  1. Streaming de un solo agente (single-agent streamed output)
  2. Ejecución paralela + selección del mejor resultado (parallelization + best-pick)
  3. Manager con herramientas (tool-use orchestration, sin handoff)
  4. Manager con handoff a un agente especializado (handoff pattern)
"""

import os
import asyncio
from typing import Dict

from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

# ---------------------------------------------------------------------------
# Configuración: carga de variables de entorno desde el archivo .env
# Se requieren: SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO
# ---------------------------------------------------------------------------
load_dotenv(override=True)

# Dirección del remitente verificado en SendGrid (leída desde .env)
_FROM_EMAIL: str = os.environ.get("EMAIL_FROM", "")
# Dirección del destinatario de prueba/producción (leída desde .env)
_TO_EMAIL: str = os.environ.get("EMAIL_TO", "")


def _get_sendgrid_client() -> sendgrid.SendGridAPIClient:
    """Crea y retorna un cliente SendGrid autenticado con la API key del entorno.

    Raises:
        EnvironmentError: si SENDGRID_API_KEY no está definida en el entorno.
    """
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "La variable de entorno SENDGRID_API_KEY no está definida. "
            "Agrégala a tu archivo .env antes de ejecutar el programa."
        )
    return sendgrid.SendGridAPIClient(api_key=api_key)


def _validate_email_config() -> None:
    """Verifica que las direcciones de email estén configuradas en el entorno.

    Raises:
        EnvironmentError: si EMAIL_FROM o EMAIL_TO no están definidas.
    """
    missing = [var for var in ("EMAIL_FROM", "EMAIL_TO") if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(
            f"Las siguientes variables de entorno son obligatorias y no están definidas: "
            f"{', '.join(missing)}. Agrégalas a tu archivo .env."
        )


def send_test_email() -> None:
    """Envía un email de prueba para verificar que la integración con SendGrid funciona.

    El remitente y destinatario se obtienen de las variables de entorno
    EMAIL_FROM y EMAIL_TO (definidas en el archivo .env).
    """
    _validate_email_config()
    sg = _get_sendgrid_client()
    from_email = Email(_FROM_EMAIL)                          # remitente verificado en SendGrid
    to_email = To(_TO_EMAIL)                                 # destinatario de prueba
    content = Content("text/plain", "This is an important test email")
    mail = Mail(from_email, to_email, "Test email", content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print("Test email status:", response.status_code)


@function_tool
def send_email(body: str) -> Dict[str, str]:
    """Send out an email with the given body to all sales prospects.

    El remitente y destinatario se leen desde las variables de entorno
    EMAIL_FROM y EMAIL_TO para evitar credenciales hardcodeadas en el código.
    """
    _validate_email_config()
    sg = _get_sendgrid_client()
    from_email = Email(_FROM_EMAIL)                          # remitente verificado en SendGrid
    to_email = To(_TO_EMAIL)                                 # destinatario del email de ventas
    content = Content("text/plain", body)
    mail = Mail(from_email, to_email, "Sales email", content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success"}


@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body to all sales prospects.

    El remitente y destinatario se leen desde las variables de entorno
    EMAIL_FROM y EMAIL_TO para evitar credenciales hardcodeadas en el código.
    """
    _validate_email_config()
    sg = _get_sendgrid_client()
    from_email = Email(_FROM_EMAIL)                          # remitente verificado en SendGrid
    to_email = To(_TO_EMAIL)                                 # destinatario del email HTML
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success"}

# ---------------------------------------------------------------------------
# Instrucciones de los agentes de ventas
# Cada agente tiene un estilo de escritura distinto para generar diversidad
# en los borradores y luego elegir el mejor.
# ---------------------------------------------------------------------------

# Agente 1: tono profesional y serio
instructions1 = (
    "You are a sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write professional, serious cold emails."
)

# Agente 2: tono cercano y con humor para aumentar la tasa de respuesta
instructions2 = (
    "You are a humorous, engaging sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write witty, engaging cold emails that are likely to get a response."
)

# Agente 3: tono directo y conciso (orientado a prospectos ocupados)
instructions3 = (
    "You are a busy sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write concise, to the point cold emails."
)

# ---------------------------------------------------------------------------
# Agentes de ventas: cada uno genera un borrador con un estilo diferente
# ---------------------------------------------------------------------------
sales_agent1 = Agent(
    name="Professional Sales Agent",
    instructions=instructions1,
    model="gpt-4o-mini",
)

sales_agent2 = Agent(
    name="Engaging Sales Agent",
    instructions=instructions2,
    model="gpt-4o-mini",
)

sales_agent3 = Agent(
    name="Busy Sales Agent",
    instructions=instructions3,
    model="gpt-4o-mini",
)

# Agente selector: elige el mejor borrador simulando ser el destinatario
sales_picker = Agent(
    name="sales_picker",
    instructions=(
        "You pick the best cold sales email from the given options. "
        "Imagine you are a customer and pick the one you are most likely to respond to. "
        "Do not give an explanation; reply with the selected email only."
    ),
    model="gpt-4o-mini",
)

# ---------------------------------------------------------------------------
# Agentes auxiliares para formateo del email (asunto y HTML)
# ---------------------------------------------------------------------------

# Instrucciones para el redactor de asuntos
subject_instructions = (
    "You can write a subject for a cold sales email. "
    "You are given a message and you need to write a subject for an email that is likely to get a response."
)

# Instrucciones para el convertidor de texto a HTML
html_instructions = (
    "You can convert a text email body to an HTML email body. "
    "You are given a text email body which might have some markdown "
    "and you need to convert it to an HTML email body with simple, clear, compelling layout and design."
)

# Agente que escribe el asunto; se expone como herramienta para otros agentes
subject_writer = Agent(
    name="Email subject writer",
    instructions=subject_instructions,
    model="gpt-4o-mini",
)
subject_tool = subject_writer.as_tool(
    tool_name="subject_writer",
    tool_description="Write a subject for a cold sales email",
)

# Agente que convierte texto plano/markdown a HTML; se expone como herramienta
html_converter = Agent(
    name="HTML email body converter",
    instructions=html_instructions,
    model="gpt-4o-mini",
)
html_tool = html_converter.as_tool(
    tool_name="html_converter",
    tool_description="Convert a text email body to an HTML email body",
)

# ---------------------------------------------------------------------------
# Patrón 3: Manager con herramientas (Tool-use Orchestration, sin handoff)
# El Sales Manager llama a los tres agentes como herramientas, elige el mejor
# borrador y lo envía directamente con send_email (email de texto plano).
# ---------------------------------------------------------------------------
def build_sales_manager_simple():
    description = "Write a cold sales email"

    # Convertir cada agente en una herramienta callable para el manager
    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

    tools = [tool1, tool2, tool3, send_email]

    instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
 
2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
 
3. Use the send_email tool to send the best email (and only the best email) to the user.
 
Crucial Rules:
- You must use the sales agent tools to generate the drafts — do not write them yourself.
- You must send ONE email using the send_email tool — never more than one.
"""

    sales_manager = Agent(
        name="Sales Manager",
        instructions=instructions,
        tools=tools,
        model="gpt-4o-mini",
    )
    return sales_manager

# ---------------------------------------------------------------------------
# Patrón 4: Manager con handoff a agente especializado (Handoff Pattern)
# El Sales Manager genera y evalúa borradores, luego hace handoff al
# Email Manager para que este formatee el correo en HTML y lo envíe.
# ---------------------------------------------------------------------------
def build_sales_manager_with_handoff():
    description = "Write a cold sales email"

    # Los agentes de ventas se exponen como herramientas para el manager
    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

    tools = [tool1, tool2, tool3]
    # Lista de agentes a los que el manager puede hacer handoff
    handoffs = [build_email_manager()]

    sales_manager_instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_agent tools.
 
Follow these steps carefully:
1. Generate Drafts: Use all three sales_agent tools to generate three different email drafts. Do not proceed until all three drafts are ready.
 
2. Evaluate and Select: Review the drafts and choose the single best email using your judgment of which one is most effective.
You can use the tools multiple times if you're not satisfied with the results from the first try.
 
3. Handoff for Sending: Pass ONLY the winning email draft to the 'Email Manager' agent. The Email Manager will take care of formatting and sending.
 
Crucial Rules:
- You must use the sales agent tools to generate the drafts — do not write them yourself.
- You must hand off exactly ONE email to the Email Manager — never more than one.
"""

    sales_manager = Agent(
        name="Sales Manager",
        instructions=sales_manager_instructions,
        tools=tools,
        handoffs=handoffs,
        model="gpt-4o-mini",
    )
    return sales_manager

# ---------------------------------------------------------------------------
# Email Manager: agente especializado al que el Sales Manager hace handoff.
# Se encarga de: escribir el asunto, convertir el cuerpo a HTML y enviarlo.
# ---------------------------------------------------------------------------
def build_email_manager():
    tools = [subject_tool, html_tool, send_html_email]

    instructions = (
        "You are an email formatter and sender. You receive the body of an email to be sent. "
        "You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. "
        "Finally, you use the send_html_email tool to send the email with the subject and HTML body."
    )

    emailer_agent = Agent(
        name="Email Manager",
        instructions=instructions,
        tools=tools,
        model="gpt-4o-mini",
        handoff_description="Convert an email to HTML and send it",
    )
    return emailer_agent

# ---------------------------------------------------------------------------
# Patrón 1: Streaming de un solo agente
# Muestra los tokens del LLM en tiempo real usando Runner.run_streamed
# ---------------------------------------------------------------------------
async def demo_streamed_email() -> None:
    result = Runner.run_streamed(sales_agent1, input="Write a cold sales email")
    # Imprimir cada fragmento de texto (token) a medida que llega del modelo
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)
    print()  # salto de línea al final


# ---------------------------------------------------------------------------
# Patrón 2: Ejecución paralela + selección del mejor resultado
# Los tres agentes se ejecutan en paralelo con asyncio.gather;
# luego un agente selector elige el mejor borrador.
# ---------------------------------------------------------------------------
async def demo_parallel_and_pick_best() -> None:
    message = "Write a cold sales email"

    # Lanzar los tres agentes en paralelo para reducir la latencia total
    with trace("Parallel cold emails"):
        results = await asyncio.gather(
            Runner.run(sales_agent1, message),
            Runner.run(sales_agent2, message),
            Runner.run(sales_agent3, message),
        )

    outputs = [result.final_output for result in results]

    print("\n=== Generated emails ===\n")
    for output in outputs:
        print(output + "\n\n")

    # Concatenar todos los borradores para que el selector los evalúe juntos
    emails = "Cold sales emails:\n\n" + "\n\nEmail:\n\n".join(outputs)

    with trace("Selection from sales people"):
        best = await Runner.run(sales_picker, emails)

    print("\n=== Best sales email ===\n")
    print(best.final_output)


async def demo_sales_manager_simple() -> None:
    """Demo del patrón Manager con herramientas: genera borradores y envía email de texto plano."""
    sales_manager = build_sales_manager_simple()
    message = "Send a cold sales email addressed to 'Dear CEO'"

    with trace("Sales manager"):
        result = await Runner.run(sales_manager, message)

    print("Sales manager final output:")
    print(result.final_output)


async def demo_sales_manager_with_handoff() -> None:
    """Demo del patrón Handoff: el Sales Manager delega el envío al Email Manager (HTML)."""
    sales_manager = build_sales_manager_with_handoff()
    message = "Send out a cold sales email addressed to Dear CEO from Alice"

    with trace("Automated SDR"):
        result = await Runner.run(sales_manager, message)

    print("Automated SDR final output:")
    print(result.final_output)

if __name__ == "__main__":
    # 1) Probar que SendGrid funciona
    print("== Testing SendGrid ==")
    send_test_email()

    # 2) Demostración de streaming
    print("\n== Streaming single email ==")
    asyncio.run(demo_streamed_email())

    # 3) Paralelo + picker
    print("\n== Parallel generation + best email picker ==")
    asyncio.run(demo_parallel_and_pick_best())

    # 4) Sales Manager simple (usa tools, envía email plano)
    print("\n== Sales Manager with tools (no handoff) ==")
    asyncio.run(demo_sales_manager_simple())

    # 5) Sales Manager con handoff a Email Manager (HTML + envío)
    print("\n== Sales Manager with handoff to Email Manager ==")
    asyncio.run(demo_sales_manager_with_handoff())
