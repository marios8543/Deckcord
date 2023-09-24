# Deckcord
## Discord on the Deck, made easy

#### Huge thanks to [@aagaming](https://github.com/AAGaming00) for his enormous contributions towards getting mic working on the SteamClient tab, as well as his general support throughout the development of this plugin.

## Features
- Runs web discord as a separate tab in the background.
- Open/Close easily while in-game from the main menu.
- Mute/Deafen/Disconnect and check members in your channel from the QAM.
- One-button post steam screenshots to your recent channels.
- Show your current game as playing status.
- Get notifications for DMs and pings in-game.
- Push-to-talk support, with physical keybind to rear buttons. (WIP)
- [Vencord](https://vencord.dev/) gets injected automatically before discord is loaded. It's needed to access a lot of the functionality that allows the plugin to do cool stuff, but also gives ya access to tons of other cool stuff.

## Issues
- **IMPORTANT:** Deafen doesn't work. Rather, I believe you appear as deafened to others but can still hear them. This has to do with the peculiarities of enabling the Discord MediaEngine in the unique environment of the BrowserView, along with the rest of the tricks needed to get microphone input working there. **Better not enable deafen at all, or let others know what's up**. I will try to fix this soon.
- Only the message input field is patched to allow the on-screen keyboard to pop-up. So no text input anywhere else (search, login, etc). You'll need some input method to type in your login credentials (e.g external keyboard)
- On first boot, the backend does not start for some reason. If you just started your deck and it doesn't work, try reloading the plugin.