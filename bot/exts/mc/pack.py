import asyncio
import logging
from datetime import datetime
from itertools import cycle
from pathlib import Path
from typing import Any, AsyncIterator

from async_timeout import timeout
from discord import (Attachment, ButtonStyle, Embed, File, Interaction,
                     Message, SelectOption, SlashCommandGroup, User, ui)
from discord.commands import ApplicationContext, permissions
from discord.ext import commands
from pydub import AudioSegment

from bot.bot import Bot
from bot.core import constants, settings
from bot.utils.checks import is_url_supported
from bot.utils.formatters import format_bytes

log = logging.getLogger(__name__)


class Modal(ui.Modal):
    """Represents a modal."""

    def __init__(self, title: str, *children: ui.InputText):
        super().__init__(title)

        # Required for detecting when the modal is closed.
        loop = asyncio.get_running_loop()
        self._stopped: asyncio.Future[bool] = loop.create_future()

        # Add children.
        for child in children:
            self.add_item(child)

    async def callback(self, interaction: Interaction) -> None:
        """Runs whenever the modal is closed."""
        # Respond to the interaction.
        await interaction.response.send_message("Modal closed.", ephemeral=True)

        # Stop the modal.
        self.stop()

    async def wait(self) -> bool:
        """Waits for the modal to be closed."""
        return await self._stopped

    def stop(self) -> None:
        """Stops listening to interaction events from the modal."""
        if not self._stopped.done():
            self._stopped.set_result(True)


class Button(ui.Button):
    """Represents a button."""

    def __init__(
            self,
            label: str,
            style: ButtonStyle = ButtonStyle.primary,
            first: bool = False,
            modal: Modal = None
    ) -> None:
        super().__init__(label=label, style=style)

        self.first = first
        self.modal = modal

    async def callback(self, interaction: Interaction) -> None:
        """Runs whenever the button is pressed."""
        # If the modal is set, send it to the interaction.
        if self.modal is not None:
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()

        self.view.value = self.first
        self.view.stop()


class SoundDropdown(ui.Select):
    """Represents a dropdown for selecting a sound."""

    def __init__(self, sound_files: list[tuple[Message, Attachment]], modal: Modal = None) -> None:
        # Remove all duplicate names from the list.
        seen = set()
        sound_files = {
            (message, attachement) for message, attachement in sound_files
            if attachement.filename not in seen and not seen.add(attachement.filename)
        }

        # Set the options that will be presented inside the dropdown.
        options = [
            SelectOption(
                label=attachment.filename.rsplit(".", maxsplit=1)[0],  # Remove the extension from the filename.
                value=attachment.filename,
                description=f"{attachment.description} ({format_bytes(attachment.size, precision=2)})",
                emoji="🎵"
            ) for msg, attachment in sorted(sound_files, key=lambda x: x[1].filename)
        ]

        # The placeholder is what will be shown when no option is chosen.
        super().__init__(
            placeholder="Choose a sound file...",
            min_values=1,
            max_values=1,
            options=options,
        )

        self.modal = modal

    async def callback(self, interaction: Interaction) -> None:
        """Runs whenever the options are selected."""
        # If the modal is set, send it to the interaction.
        if self.modal is not None:
            await interaction.response.send_modal(self.modal)
            await self.modal.wait()

        self.view.value = self.values[0]
        self.view.stop()


class View(ui.View):
    """Represents a view."""

    def __init__(self, *items: ui.Item, **kwargs) -> None:
        super().__init__(*items, **kwargs)

        # Set the default value to None.
        self.value = None


class Pack(commands.Cog):
    """Manage the server's ressource pack."""

    def __init__(self, bot: Bot):
        self.bot = bot

    pack = SlashCommandGroup(
        "pack", "Manage the ressource pack.",
        guild_ids=settings.guild_ids,
        permissions=[permissions.CommandPermission(settings.roles.admin, 1)]
    )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Runs when the bot is ready."""
        # Register the persistent view.
        self.bot.add_view(PersistentView(self))
        log.debug("Registered the pack managing process persistent view")

    @pack.command()
    async def manage(self, ctx: ApplicationContext, user: User, link: str) -> None:
        """Manually start the pack managing process for a given user."""
        log.info(f"Starting the pack managing process for {user} (ID: {user.id})")

        # Send a response message to the user if ctx is not None.
        if ctx is not None:
            await ctx.respond(f"Starting the pack managing process for <@{user.id}>", ephemeral=True)

        if link:
            # Check if the link is valid.
            if not is_url_supported(link):
                log.debug(f"Pack managing process ended, the link is not supported (ID: {user.id})")

                # Final response to the user.
                embed = Embed(
                    colour=constants.colours.red,
                    description=f"The [link]({link}) is not supported."
                )

                await user.send(embed=embed)
                return

            # Continue if the link is supported.
            log.debug(f"Supported link received {link} (ID: {user.id})")

            with self.bot.ydl as ydl:
                # Extract info from the link.
                info = ydl.extract_info(link, download=False)
                log.debug(f"Extracted info from the link (ID: {user.id})")

                original_duration = int(info["duration"])
                minutes, seconds = divmod(original_duration, 60)  # Convert seconds into minutes.
                date = datetime.strptime(info["upload_date"], "%Y%m%d")  # Convert `%Y%m%d` to a datetime object.

                size = int(info["filesize"])
                size_str = format_bytes(int(info["filesize"]))  # Convert bytes into MB.

                # Create the embed.
                embed = Embed(
                    title=info["title"],
                    url=link,
                    colour=constants.colours.light_blue,
                    timestamp=date,
                    description="\n".join([
                        f"• Duration: **{minutes:02}:{seconds:02}**",
                        f"• Size: **{size_str}**",
                        f"• Format: **{info['format']}**"
                    ])
                )

                # Set the thumbnail and the footer.
                embed.set_thumbnail(url=info["thumbnail"])
                embed.set_footer(text=f"{info['view_count']:,} views", icon_url=constants.images.youtube)

                # Calculate what the duration should be so that the size becomes bellow the maximum.
                ratio = (minutes * 60 + seconds) / size

                max_duration = int(settings.audio.max_filesize * ratio)

                # Make sure the max duration is less than the original duration.
                if max_duration > original_duration:
                    max_duration = original_duration

                max_minutes, max_seconds = divmod(max_duration, 60)  # Convert seconds into minutes.

                # Ask the user if he wants to add the sound file.
                buttons = [
                    Button(
                        "Add sound file",
                        ButtonStyle.green,
                        first=True,
                        modal=Modal(
                            "Video download settings",
                            ui.InputText(label="Minecraft event name", placeholder="music.rickroll"),
                            ui.InputText(
                                label="Start time",
                                placeholder="00:00",
                                required=False,
                                min_length=5,
                                max_length=5
                            ),
                            ui.InputText(
                                label="End time",
                                placeholder=f"Maximum end time: {max_minutes:02}:{max_seconds:02}",
                                required=size > settings.audio.max_filesize,
                                min_length=5,
                                max_length=5
                            )
                        )
                    ), Button("Cancel", ButtonStyle.red),
                ]

                view = View(*buttons, timeout=settings.audio.button_timeout * 2)

                # Send and wait for the user to choose a button.
                await user.send(embed=embed, view=view)
                await view.wait()

                if view.value is None:
                    log.debug(f"Pack managing process ended, no button was chosen in time (ID: {user.id})")

                    # Final response to the user.
                    embed = Embed(
                        colour=constants.colours.red,
                        description="You did not select a button in time."
                    )

                    await user.send(embed=embed)
                    return
                elif view.value:
                    # Get the values from the modal response.
                    event_name = buttons[0].modal.children[0].value
                    start_time = buttons[0].modal.children[1].value or "00:00"
                    end_time = buttons[0].modal.children[2].value or f"{minutes:02}:{seconds:02}"

                    # Check if the start time and the end time are valid.
                    try:
                        start_time = datetime.strptime(start_time, "%M:%S")
                        end_time = datetime.strptime(end_time, "%M:%S")
                    except ValueError:
                        log.debug(f"Invalid start time or end time (ID: {user.id})")

                        # Final response to the user.
                        embed = Embed(
                            colour=constants.colours.red,
                            description="The start time or the end time is invalid."
                        )

                        await user.send(embed=embed)
                        return

                    # Convert the start time and the end time to seconds.
                    start_time = start_time.minute * 60 + start_time.second
                    end_time = end_time.minute * 60 + end_time.second

                    if start_time or end_time != original_duration:
                        # Check if the start time is valid.
                        if start_time > original_duration:
                            log.debug(f"Pack managing process ended, the start time is invalid (ID: {user.id})")

                            # Final response to the user.
                            embed = Embed(
                                colour=constants.colours.red,
                                description="The start time is invalid."
                            )

                            await user.send(embed=embed)
                            return

                        # Check if the end time is valid.
                        if end_time > max_duration:
                            log.debug(f"Pack managing process ended, the end time is invalid (ID: {user.id})")

                            # Final response to the user.
                            embed = Embed(
                                colour=constants.colours.red,
                                description="The end time is invalid."
                            )

                            await user.send(embed=embed)
                            return

                        # Check if the start time is greater than the end time.
                        if start_time > end_time:
                            log.debug(f"Pack managing process ended, the start time is too big (ID: {user.id})")

                            # Final response to the user.
                            embed = Embed(
                                colour=constants.colours.red,
                                description="The start time is greater than the end time."
                            )

                            await user.send(embed=embed)
                            return

                    # Check if the download size is too big.
                    if size > settings.audio.max_download_size:
                        # Final response to the user.
                        max_download_size_str = format_bytes(settings.audio.max_download_size)
                        embed = Embed(
                            colour=constants.colours.red,
                            description=f"File size must be less than **{max_download_size_str}**."
                        )

                        log.debug(f"Pack managing process ended, file size is too big (ID: {user.id})")
                        await user.send(embed=embed)
                        return

                    log.debug(f"Downloading the sound file (ID: {user.id})")

                    # Download the sound file in the background pool.
                    self.bot.pool.submit(self.bot.ydl.download, [link])

                    # Create the embed.
                    embed = Embed(
                        description="\n".join([
                            "• Percentage: **...**",
                            "• Speed: **...**",
                            "• Time remaining: **...**"
                        ])
                    )

                    # Send the initial embed.
                    msg: Message = await user.send(embed=embed)

                    async with timeout(settings.audio.download_timeout):
                        # Keep editing the embed with the status of the download.
                        while self.bot.ydl_progress["status"] != "finished":
                            if self.bot.ydl_progress["status"] == "downloading":
                                # Create the embed.
                                embed = Embed(
                                    colour=constants.colours.orange,
                                    description="\n".join([
                                        f"• Percentage: **{self.bot.ydl_progress['_percent_str']}**",
                                        f"• Speed: **{self.bot.ydl_progress['_speed_str']}**",
                                        f"• Time remaining: **{self.bot.ydl_progress['_eta_str']}**"
                                    ])
                                )

                                # Edit the embed.
                                await msg.edit(embed=embed)
                                await asyncio.sleep(1)
                            elif self.bot.ydl_progress["status"] in {"downloading", ""}:
                                continue
                            else:
                                log.debug(f"Status {self.bot.ydl_progress['status']}, download failed (ID: {user.id})")
                                break

                    # Fetch the pack channel from its id.
                    pack_channel = self.bot.get_channel(settings.channels.pack)

                    # Replace the extension with .ogg.
                    filename = Path(self.bot.ydl_progress["filename"])

                    # Normalize the sound file.
                    task = self.bot.pool.submit(self.normalize_sound, filename, start_time, end_time)

                    # Create a loading animation cycle.
                    loading_cycle = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

                    # Create a loading embed.
                    while not task.done():
                        embed = Embed(
                            colour=constants.colours.orange,
                            description="\n".join([
                                f"• Status: **Converting {next(loading_cycle)}**",
                                "• Speed: **...**",
                                "• Time remaining: **...**"
                            ])
                        )

                        # Edit the embed.
                        await msg.edit(embed=embed)
                        await asyncio.sleep(0.25)

                    # Format the time elapsed into minutes and seconds.
                    minutes, seconds = divmod(int(self.bot.ydl_progress.get("elapsed", 0)), 60)
                    downloaded_bytes = format_bytes(self.bot.ydl_progress['total_bytes'])

                    # Create the embed.
                    embed = Embed(
                        colour=constants.colours.bright_green,
                        description="\n".join([
                            f"• Status: **{self.bot.ydl_progress['status']}**",
                            f"• Downloaded bytes: **{downloaded_bytes}**",
                            f"• Elapsed: **{minutes:02}:{seconds:02}**"
                        ])
                    )

                    # Display the final status.
                    log.debug(f"Downloaded {downloaded_bytes} in {minutes:02}:{seconds:02} (ID: {user.id})")
                    await msg.edit(embed=embed)

                    # Make sure to reset the progress status.
                    self.bot.ydl_progress["status"] = ""

                    # Rename the filename extension to .ogg.
                    filename = filename.with_suffix(".ogg")
                    log.debug(f"Renamed the file to {filename} (ID: {user.id})")

                    # Create the file object.
                    file = File(filename, f"custom.{event_name}.ogg")

                    # Send the file to the pack channel.
                    msg: Message = await pack_channel.send(file=file)
                    log.debug(f"Sent the file {file.filename} to the pack channel (ID: {user.id})")

                    # Final response to the user.
                    embed = Embed(
                        colour=constants.colours.bright_green,
                        description=f"Added [Sound file]({msg.jump_url}) to the pack."
                    )

                    await user.send(embed=embed)
                else:
                    log.debug(f"Pack managing process ended, the user cancelled (ID: {user.id})")

                    # Final response to the user.
                    embed = Embed(
                        colour=constants.colours.red,
                        description="You cancelled the process."
                    )

                    await user.send(embed=embed)
                    return
        else:
            # Fetch sound files from the pack channel.
            sound_files = [(msg, attachement) async for msg, attachement in self.get_sound_files()]
            log.debug(f"Fetched {len(sound_files)} sound files (ID: {user.id})")

            # End process if there are no sound files.
            if not sound_files:
                log.debug(f"Pack managing process ended, no sound files were found (ID: {user.id})")

                # Final response to the user.
                embed = Embed(
                    colour=constants.colours.red,
                    description="There are no sound files in the pack."
                )

                await user.send(embed=embed)
                return

            # Select a sound file to remove.
            view = View(SoundDropdown(sound_files))

            # Send and wait for the user to select a sound file.
            await user.send(f"<@{user.id}>, Please select a sound file to remove.", view=view)
            await view.wait()

            if view.value is None:
                log.debug(f"Pack managing process ended, no sound file was selected in time (ID: {user.id})")

                # Final response to the user.
                embed = Embed(
                    colour=constants.colours.red,
                    description="You did not choose a sound file in time."
                )

                await user.send(embed=embed)
                return
            else:
                log.debug(f"Sound file {view.value} was selected (ID: {user.id})")

                # Find the message with the same attachement.
                for msg, attachement in sound_files:
                    if attachement.filename == view.value:
                        # Delete the message.
                        await msg.delete()

                        # Final response to the user.
                        embed = Embed(
                            colour=constants.colours.bright_green,
                            description=f"`{attachement.filename}` was successfully removed."
                        )

                        await user.send(embed=embed)
                        log.debug(f"Sound file {attachement.filename} was successfully removed (ID: {user.id})")

                        break

        # Regenerate the ressource pack.
        log.debug(f"Pack managing process ended successfully (ID: {user.id})")

    @pack.command()
    async def post(self, ctx: ApplicationContext) -> None:
        """Post the pack to the server."""
        # Create the view and the embed.
        view = PersistentView(self)
        embed = Embed(
            title="Manage the ressource pack",
            description="This system is for managing the server's ressource pack, adding or removing sounds."
        )

        # Send the embed to the channel.
        await ctx.respond(embed=embed, view=view)

    @staticmethod
    def normalize_sound(
            path: Path, start_time: int = 0, end_time: int = 0, out_format: str = "ogg",
            bitrate: str = settings.audio.bitrate, sample_rate: int = settings.audio.sample_rate,
            fade_duration: int = settings.audio.fade_duration, loudness: int = settings.audio.loudness
    ) -> Any:
        """
        Normalize an audio file using pydub.

        Args:
            path (Path): The path to the sound file.
            start_time (int): The start time in seconds.
            end_time (int): The end time in seconds.
            out_format: The output format.
            bitrate: The bitrate of the output file.
            sample_rate: The sample rate of the output file.
            fade_duration: The duration of the fade in and out in seconds.
            loudness: The loudness of the output file.
        """
        sound = AudioSegment.from_file(path)

        if end_time:
            # Cut the sound to the correct length.
            sound = sound[start_time * 1000:end_time * 1000]

        if fade_duration:
            # Fade in and out.
            sound = sound.fade_in(fade_duration).fade_out(fade_duration)

        if loudness:
            # Normalize the sound.
            loudness_difference = loudness - sound.dBFS
            sound = sound.apply_gain(loudness_difference)

        # Convert and export the sound to the correct format.
        return sound.export(
            path.with_suffix(f".{out_format}"),
            format=out_format,
            parameters=["-ar", str(sample_rate)],
            bitrate=bitrate
        )

    async def get_sound_files(self) -> AsyncIterator[Attachment]:
        """Returns a list of sound files from the pack channel."""
        channel = self.bot.get_channel(settings.channels.pack)
        messages = await channel.history(limit=100).flatten()

        for msg in messages:
            for attachment in msg.attachments:
                if attachment.content_type == "audio/ogg":
                    yield msg, attachment


class PersistentView(ui.View):
    """Represents the starting persistent view."""

    def __init__(self, cog: Pack):
        super().__init__(timeout=None)

        self.cog = cog

    @ui.button(label="Upload from YouTube", style=ButtonStyle.green, custom_id="persistent_view:upload_sound_file")
    async def upload(self, button: ui.Button, interaction: Interaction) -> None:
        """Runs whenever the upload button is pressed."""
        modal = Modal(
            "Upload from YouTube",
            ui.InputText(
                label="URL",
                placeholder="https://www.youtube.com/watch?v=...",
                required=True
            )
        )

        # Send and wait for the modal.
        await interaction.response.send_modal(modal)
        await modal.wait()

        # Get the URL from the modal.
        url = modal.children[0].value

        # Start the upload process.
        await self.cog.manage(self.cog, None, interaction.user, url)

    @ui.button(label="Remove a sound file", style=ButtonStyle.red, custom_id="persistent_view:remove_sound_file")
    async def remove(self, button: ui.Button, interaction: Interaction) -> None:
        """Runs whenever the remove button is pressed."""
        # Start the upload process.
        await interaction.response.defer()
        await self.cog.manage(self.cog, None, interaction.user, None)


def setup(bot: Bot) -> None:
    """Load the `Pack` cog."""
    bot.add_cog(Pack(bot))
