import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from core.agent import JarvisAgent
from core.speaker import ElevenLabsSpeaker
from core.listener import VoiceListener

console = Console()

def run_hands_free_loop(agent: JarvisAgent, speaker: ElevenLabsSpeaker, listener: VoiceListener):
    """Continuous hands-free voice loop."""
    console.print(
        Panel.fit(
            "[bold green]🎙️ JARVIS Hands-Free Mode Active[/bold green]\n"
            "[white]Speak into your microphone naturally. JARVIS will listen and respond.[/white]\n"
            "[dim]Say 'exit' or press Ctrl+C to stop.[/dim]",
            border_style="green"
        )
    )

    welcome_msg = "Hands free mode activated. I am listening, sir."
    console.print(f"[bold cyan]JARVIS:[/bold cyan] {welcome_msg}")
    if speaker.api_key:
        speaker.speak(welcome_msg)

    while True:
        try:
            with console.status("[bold cyan]🎙️ Listening... (Speak now)[/bold cyan]", spinner="arc"):
                spoken_text = listener.listen(silence_limit=1.3, max_duration=20.0)

            if not spoken_text:
                continue

            console.print(f"\n[bold green]You (Voice):[/bold green] {spoken_text}")

            if spoken_text.lower() in ["exit", "quit", "shutdown", "stop listening"]:
                farewell = "Going to standby. Have a good day, sir."
                console.print(f"[bold cyan]JARVIS:[/bold cyan] {farewell}")
                if speaker.api_key:
                    speaker.speak(farewell)
                break

            with console.status("[bold cyan]JARVIS is reasoning and orchestrating...[/bold cyan]", spinner="dots"):
                response = agent.chat(spoken_text)

            console.print(f"\n[bold cyan]JARVIS:[/bold cyan]\n{response}")

            if speaker.api_key:
                speaker.speak(response)

        except KeyboardInterrupt:
            console.print("\n[dim]Hands-free mode stopped by user.[/dim]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error in voice loop:[/bold red] {e}")


def main():
    hands_free_arg = "--hands-free" in sys.argv
    speaker = ElevenLabsSpeaker()
    listener = VoiceListener()

    voice_out_status = "[green]Enabled (ElevenLabs)[/green]" if speaker.api_key else "[dim]Disabled[/dim]"

    console.print(
        Panel.fit(
            "[bold cyan]🤖 JARVIS Agent System[/bold cyan]\n"
            f"[white]Voice Output:[/white] {voice_out_status} | [white]Mic Input:[/white] [green]Ready[/green]\n"
            "[dim]Type your message, or type 'mic' to speak once, or 'handsfree' for continuous mode[/dim]",
            border_style="cyan"
        )
    )

    try:
        agent = JarvisAgent()
        console.print(f"[bold green]✔ Central Brain online![/bold green] (Model: {agent.model_name})\n")
    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        sys.exit(1)

    if hands_free_arg:
        run_hands_free_loop(agent, speaker, listener)
        return

    voice_active = True

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You (Type or press Enter for mic)[/bold green]").strip()

            # If user pressed enter without typing or typed 'mic'
            if not user_input or user_input.lower() in ["mic", "/mic", "listen"]:
                with console.status("[bold cyan]🎙️ Listening to your microphone...[/bold cyan]", spinner="arc"):
                    spoken = listener.listen(silence_limit=1.3)
                if not spoken:
                    console.print("[dim](No speech detected. Type your message or try again)[/dim]")
                    continue
                user_input = spoken
                console.print(f"[bold green]Heard:[/bold green] {user_input}")

            if user_input.lower() in ["exit", "quit"]:
                farewell = "Shutting down systems. Goodbye, sir."
                console.print(f"[dim]{farewell}[/dim]")
                if voice_active and speaker.api_key:
                    speaker.speak(farewell)
                break

            if user_input.lower() in ["handsfree", "hands-free", "/handsfree"]:
                run_hands_free_loop(agent, speaker, listener)
                continue

            if user_input.lower() == "voice on":
                voice_active = True
                console.print("[green]Voice output turned ON.[/green]")
                continue

            if user_input.lower() == "voice off":
                voice_active = False
                console.print("[yellow]Voice output turned OFF.[/yellow]")
                continue

            with console.status("[bold cyan]JARVIS is reasoning...[/bold cyan]", spinner="dots"):
                response = agent.chat(user_input)

            console.print(f"\n[bold cyan]JARVIS:[/bold cyan]\n{response}")

            if voice_active and speaker.api_key:
                speaker.speak(response)

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted by user. Exiting...[/dim]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error during execution:[/bold red] {e}")

if __name__ == "__main__":
    main()
