# Custom Modder for Deadly Boss Mods

This is a python3 script that automatically edits World of Warcraft DBM addon files, adding chat messages before something is going to happen. Perfect for reminding your co-raiders (or yourself) of a particular event in the encounter, or simply to add a little RP.

## Usage

1. Make a copy of `config.template.json` and rename it `config.json`
2. Run `dbm-modder.py`

By default, the script will look for the addon files at the default install location of Windows 7+ (typically `C:\Users\Public\Games\World of Warcraft\Interface\Addons`). If your `Addons` folder is not found there, the configuration file should be modified for your environment.

**IMPORTANT NOTE:** Your changes will be lost as soon as you update/replace DBM. To restore your changes, simply run the script again.

### Config File Format

The configuration file is in [JSON format](http://www.json.org/). Here is a documented sample.

```JavaScript
{
  /**
   * Indicates the config version number.
   * @type Number
   * @required true
   */
  "version": 2,

  /**
   * A custom directory to look for WoW addon files.
   * @type String
   * @required false
   * @default [[ The default WoW install directory's Addons folder ]]
   */
  "addonsDir": "G:/World of Warcraft/Interface/AddOns",

  "files": {
    /**
     * DBM file to mod. File path should be relative to addon directory.
     */
    "DBM-TombofSargeras/MaidenofVigilance.lua": {

      /**
       * Key: "premonition"
       * Section indicates advance alerts.
       */
      "premonition": {
        /**
         * Key: Timer ID
         * Corresponds to a local timer variable name in target file.
         */
        "timerBlowbackCD": {
          /**
           * A human-friendly name for the timer.
           * @required false
           * @default [[ Timer ID ]]
           */
          "alias": "Blowback Soon",

          /**
           * A custom message to follow the timer label.
           * The string can use a single option to display the expected time.
           * @required false
           * @default "%.0f seconds"
           */
          "message": "Refresh dots before %.1f!",

          /**
           * Number of seconds to display chat message ahead of event.
           * @type Number
           * @required false
           * @default 5
           */
          "seconds": 10,

          /**
           * WOWAPI channel type ID.
           * More info: https://wow.gamepedia.com/ChatTypeId
           * @type String
           * @required false
           * @default "YELL"
           */
          "channel": "SAY"
        },

        /**
         * (Second) Key: Timer ID
         * @required true
         */
        "timerMassInstabilityCD": {
          /**
           * If the template message is not to your liking, the full chat message
           * can be customized with this key.
           * The string can use a single option to display the expected time.
           * @required false
           */
          "fullMessage": "Something's coming!",
          "seconds": 4
        }
      },

      /**
       * Key: "event"
       * Section indicates immediate alerts.
       */
      "event": {
        /**
         * WOWAPI combat event ID.
         * More info: http://wowprogramming.com/docs/events
         */
        "SPELL_AURA_REMOVED": {
          /**
           * WOWAPI Spell ID.
           * You can find them over Wowhead
           */
          "235028": {

            /**
             * A human-friendly name for the spell.
             * @required false
             * @default [[ Spell ID ]]
             */
            "alias": "Bulwark Removed",

            /**
             * A custom message to follow the spell label.
             * @required false
             * @default [[ Combat event ID ]]
             */
              "message": "Interrupt!",

            /**
             * WOWAPI channel type ID.
             * More info: https://wow.gamepedia.com/ChatTypeId
             * @type String
             * @required false
             * @default "YELL"
             */
            "channel": "SAY"
          }
        },

        /**
         * (Second) Combat event
         */
        "SPELL_CAST_START": {
          "235267": {
            /**
             * If the template message is not to your liking, the full chat message
             * can be customized with this key.
             * The string can use a single option to display the expected time.
             * @required false
             */
            "fullMessage": "She's getting unstable...",
            "channel": "SAY"
          }
        }
      }
    },

    /**
     * (Second) DBM file to mod.
     */
    "DBM-TombofSargeras/FallenAvatar.lua": {
      "timerRuptureRealitiesCD": {
        "fullMessage": "Something's not right...",
        "seconds": 5,
        "channel": "SAY"
      }
    }
  }
}
```
