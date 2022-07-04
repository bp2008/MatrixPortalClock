# MatrixPortalClock
Clock software for Adafruit Matrix Portal M4.  Uses MQTT to synchronize time and load custom text which is displayed on two scrolling lines below the clockface.

![image](https://user-images.githubusercontent.com/5639911/177080414-0278940d-b21d-47f8-8c5d-bf52543f906b.png)

This clock software is based on [Network Connected RGB Matrix Clock from Adafruit](https://learn.adafruit.com/network-connected-metro-rgb-matrix-clock/overview).  I heavily modified the code and slightly modified the font and added an additional tiny font for small text rendering.

## Proprietary server software

I stripped out Adafruit's time sync code and implemented my own proprietary time sync using MQTT to communicate with a proprietary server running elsewhere (code for the server is not available).  Therefore the code in this project is not useable out-of-box, and modifications would be required to make it functional.
