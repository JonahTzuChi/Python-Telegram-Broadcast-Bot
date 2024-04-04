# Telegram Broadcast Solution

## Introduction
A Telegram Bot based solution developed with Python, designed to enhance communication and management efficiency for Telegram channel admins. It features one master bot that interacts directly with subscribers and one worker bot that handles administrative tasks and broadcasting operations.

### Master Bot
The Master Bot is designed for direct interaction with subscribers, providing them with a range of commands to enhance their experience. Below is a list of available commands along with their descriptions:

- **/follow**: 👉 Follow me on GitHub - Allows users to get the link to follow the project or the developer's GitHub page.
- **/feedback**: ✉️ Provide feedback - Users can send feedback about the bot or service directly to the admin or development team.
- **/rename**: ✏️ Change username - Enables users to change their username as stored or displayed by the bot.
- **/subscribe**: 🌟 Subscribe to the bot - Users can subscribe to receive updates, broadcasts, or notifications from the bot.
- **/unsubscribe**: 🔕 Unsubscribe from the bot - Allows users to opt out of receiving updates, broadcasts, or notifications.
- **/help**: 📋 Get command menu - Displays a list of available commands that users can interact with.

These commands are designed to provide an intuitive and engaging user experience, ensuring subscribers can easily navigate and utilize the bot's functionalities.

### Worker Bot
The Worker Bot is engineered to facilitate administrative tasks and broadcasting operations, acting as the backbone for channel or group management. It is designed primarily for use by system administrators and authorized admin users, providing a comprehensive suite of tools for subscriber and content management. Key functionalities include:

#### For System Admins:
- **Admin User Management**: 
  - **Grant admin access**: Empowers system admins to assign admin roles to selected users, enhancing control over the bot's functionalities.
  - **Revoke admin access**: Allows the removal of admin privileges, ensuring dynamic management of user roles.
  - **List allowable admin users**: Provides a clear view of all users with admin access, aiding in the efficient management of permissions.
- **Subscriber Management**: 
  - **Export subscriber list (full) in CSV format**: Facilitates the exportation of a comprehensive subscriber list, useful for analytics and backup.
  - **Upload subscriber list**: Enables the importation of subscriber lists, simplifying subscriber management across different platforms or channels.
- **Application Management**: 
  - **Delete application log**: Allows for the clearing of application logs to maintain privacy and optimize performance.
  - **Delete application data**: Permits the removal of all application data, facilitating a fresh start or clean slate when needed.

#### For Admin Users:
- **Subscriber Management**: 
  - **Get subscriber count**: Offers a quick view of the current subscriber base, essential for tracking growth and engagement.
- **Broadcast Content**: 
  - Enables the broadcasting of diverse types of content (Text, Photo, Video, Document), ensuring rich and engaging communications.
- **Media File Management**: 
  - Supports uploading and retrieval of media files, enhancing content delivery strategies.
- **File Tracking**: 
  - Prevents the rebroadcasting of identical files and allows for the resetting of file tracking, ensuring content freshness.
- **Miscellaneous**: 
  - **Get current weather**: Adds a layer of interactive content by providing weather updates.
  - **Get command menu**: Simplifies navigation and utilization of the bot's features through an accessible command list.

The Worker Bot serves as a powerful tool for administrators, streamlining the management of subscribers and content, ensuring efficient and effective broadcast operations.