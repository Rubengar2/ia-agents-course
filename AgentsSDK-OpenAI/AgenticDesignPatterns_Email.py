import os
import asyncio
from typing import Dict

from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

# Cargar variables de entorno (.env)
load_dotenv(override=True)

def send_test_email() -> None:
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("tu_email")  # remitente verificado
    to_email = To("tu_email")      # destinatario de prueba
    content = Content("text/plain", "This is an important test email")
    mail = Mail(from_email, to_email, "Test email", content).get()
    response = sg.client.mail.send.post(request_body=mail)
    print("Test email status:", response.status_code)

@function_tool
def send_email(body: str) -> Dict[str, str]:
    """Send out an email with the given body to all sales prospects"""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("tu_email")  # remitente verificado
    to_email = To("tu_email")      # destinatario
    content = Content("text/plain", body)
    mail = Mail(from_email, to_email, "Sales email", content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success"}

@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body to all sales prospects"""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
    from_email = Email("tu_email")
    to_email = To("tu_email")
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success"}

instructions1 = (
    "You are a sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write professional, serious cold emails."
)

instructions2 = (
    "You are a humorous, engaging sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write witty, engaging cold emails that are likely to get a response."
)

instructions3 = (
    "You are a busy sales agent working for ComplAI, "
    "a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. "
    "You write concise, to the point cold emails."
)

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

sales_picker = Agent(
    name="sales_picker",
    instructions=(
        "You pick the best cold sales email from the given options. "
        "Imagine you are a customer and pick the one you are most likely to respond to. "
        "Do not give an explanation; reply with the selected email only."
    ),
    model="gpt-4o-mini",
)

subject_instructions = (
    "You can write a subject for a cold sales email. "
    "You are given a message and you need to write a subject for an email that is likely to get a response."
)

html_instructions = (
    "You can convert a text email body to an HTML email body. "
    "You are given a text email body which might have some markdown "
    "and you need to convert it to an HTML email body with simple, clear, compelling layout and design."
)

subject_writer = Agent(
    name="Email subject writer",
    instructions=subject_instructions,
    model="gpt-4o-mini",
)
subject_tool = subject_writer.as_tool(
    tool_name="subject_writer",
    tool_description="Write a subject for a cold sales email",
)

html_converter = Agent(
    name="HTML email body converter",
    instructions=html_instructions,
    model="gpt-4o-mini",
)
html_tool = html_converter.as_tool(
    tool_name="html_converter",
    tool_description="Convert a text email body to an HTML email body",
)

def build_sales_manager_simple():
    description = "Write a cold sales email"

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

def build_sales_manager_with_handoff():
    description = "Write a cold sales email"

    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description=description)
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description=description)
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description=description)

    tools = [tool1, tool2, tool3]
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

async def demo_streamed_email() -> None:
    result = Runner.run_streamed(sales_agent1, input="Write a cold sales email")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)
    print()  # salto de línea al final

async def demo_parallel_and_pick_best() -> None:
    message = "Write a cold sales email"

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

    emails = "Cold sales emails:\n\n" + "\n\nEmail:\n\n".join(outputs)

    with trace("Selection from sales people"):
        best = await Runner.run(sales_picker, emails)

    print("\n=== Best sales email ===\n")
    print(best.final_output)

async def demo_sales_manager_simple() -> None:
    sales_manager = build_sales_manager_simple()
    message = "Send a cold sales email addressed to 'Dear CEO'"

    with trace("Sales manager"):
        result = await Runner.run(sales_manager, message)

    print("Sales manager final output:")
    print(result.final_output)

async def demo_sales_manager_with_handoff() -> None:
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
