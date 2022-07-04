def ScrollLabel(lbl, displayWidth, characterWidth):
    if lbl.text == None:
        return
    numChars = len(lbl.text)
    maxChars = displayWidth // characterWidth
    if numChars <= maxChars:
        if lbl.x != 0:
            lbl.x = 0
        return

    totalWidth = numChars * characterWidth
    #print("ScrollLabel", lbl.x)
    if lbl.x <= -totalWidth:
        lbl.x = 0
    else:
        lbl.x -= 1