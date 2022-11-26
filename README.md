## Spell Checker with Custom Dictionaries

<img src="https://github.com/lovac42/SpellingPolice/blob/master/screenshots/intro.png?raw=true">

## About:
If you read "The Shallows", it describes the over reliance of spell checkers in modern software. Well, the over reliance of a lot of things in modern tools... But the basic idea is that auto-correct is making us stupid.

This addon follows that idea and is off by default, but when turned on, spelling police nags you and points out all your spelling errors. It does not fix spelling mistakes for you. That's your job. This tough love approach will help you to learn to spell better.

Ankiweb Listing: https://ankiweb.net/shared/info/390813456

## Dictionaries:

The following dictionaries are installed by default:
- `glutanimate_medical.bdic` is from: https://github.com/glutanimate/hunspell-en-med-glut-workaround
- `en-US-10-1.bdic` is from the chromium browser.
- `anki.bdic` contains words for Anki usage.
- Download a drugs dictionary here: [drugs-2019.bdic.zip](https://github.com/AnKing-Memberships/spell-checker-addon/files/10060926/drugs-2019.bdic.zip)


You can add more dictionaries by downloading the dictionary files. The add-on uses .bdic files used by Chrome.

You can download more .bdic files here:
- https://github.com/cvsuser-chromium/third_party_hunspell_dictionaries 
- https://github.com/lovac42/SpellingPolice/issues/8

After downloading the .bdic files, go to `Anking > Spell Checker Dictionaries` and click the browse button. Put all your .bdic files into this "dictionaries" folder. You may need to restart Anki after installing new dictionaries.

Once you have it setup, enable or disable the dictionaries of your choice. More than one is allowed, but try to avoid language conflicts (e.g. Chinese and Japanese).

<img src="https://github.com/AnKing-Memberships/spell-checker-addon/blob/master/screenshots/setup.png?raw=true">  

<img src="https://github.com/AnKing-Memberships/spell-checker-addon/blob/master/screenshots/dictionaries.png?raw=true">  

### Custom Dictionary

You can create your own custom dictionary. Go to `Anking > Spell Checker Dictionaries` and click the 'Custom Dictionary' button. 

Add one word in each line, click Apply, then restart Anki.

<img src="https://github.com/AnKing-Memberships/spell-checker-addon/blob/master/screenshots/custom_dictionary.png?raw=true"> 


### Setup Instruction for Alternate Versions of Anki:
Alternate versions of Anki uses qt5.9 that requires a special folder called `qtwebengine_dictionaries` to be created in the anki.exe folder. It uses the qtwebengine_dictionaries directory relative to the executable. This addon will try to create it, but you will need Read-Write permissions to do so. The same applies to mac and linux, but the folder location may differ depending on your distro.


## Screenshots:

<img src="https://github.com/AnKing-Memberships/spell-checker-addon/blob/master/screenshots/editor.png?raw=true">  

<img src="https://github.com/AnKing-Memberships/spell-checker-addon/blob/master/screenshots/review.png?raw=true">  

