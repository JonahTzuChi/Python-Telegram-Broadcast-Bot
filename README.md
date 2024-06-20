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
#### For Admin Users:
- **/broadcast**: Enables the broadcasting of diverse types of content (Text, Photo, Video, Document), ensuring rich and engaging communications.
- **/upload**: Supports uploading of media files.
- **/release**: Release the operation lock.
- **/photo**: Retrieve the name of "Photo" files.
- **/document**: Retrieve the name of "Document" files.
- **/video**: Retrieve the name of "Video" files.
- **/reset_file_tracking**: Mark the file as "Not Sent" to all active subscribers. 
- **/metrics**: Offers a quick view of the current subscriber base, essential for tracking growth and engagement.
- **/terminate**: Broadcast the termination message to all subscriber.
- **/help**: Simplifies navigation and utilization of the bot's features through an accessible command list.

#### For System Admins:
- **/grant**: Empowers system admins to assign admin roles to selected users, enhancing control over the bot's functionalities.
- **/revoke**: Allows the removal of admin privileges, ensuring dynamic management of user roles.
- **/show_superuser**: Provides a clear view of all users with admin access, aiding in the efficient management of permissions.
- **/who_has_this_file**: Retrieve the namelist of subscriber who have retrieve the stated file.

The Worker Bot serves as a powerful tool for administrators, streamlining the management of subscribers and content, ensuring efficient and effective broadcast operations.