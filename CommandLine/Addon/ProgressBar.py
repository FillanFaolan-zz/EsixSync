class ProgressBar:
    maxValue = 100
    minValue = 0
    curValue = 0
    progressBarFilledChar = '#'
    progressBarUnfilledChar = '-'
    progressBarLeftBracket = '['
    progressBarRightBracket = ']'
    extContent = ""
    showProgress = True
    showItemCounter = True
    _progressBarCharLen = 25

    def __init__(self, minValue: int = 0, maxValue: int = 100):
        self.minValue = minValue
        self.maxValue = maxValue

    def GetProgressBarString(self):
        space = ' '
        progress = (self.curValue - self.minValue) / (self.maxValue - self.minValue)
        filledLength = int(progress * self._progressBarCharLen)
        if self.showItemCounter:
            progressBar = ("(%s/%s)" % (self.curValue - self.minValue, self.maxValue - self.minValue) + space)
        progressBar += self.progressBarLeftBracket
        progressBar += self.progressBarFilledChar * filledLength
        progressBar += self.progressBarUnfilledChar * (self._progressBarCharLen - filledLength)
        progressBar += self.progressBarRightBracket
        if self.showProgress:
            ext = self.extContent
            progressBar += space + ("%s" % int(progress * 100)) + "%" + ((space + ext) if ext != "" else "")
        return progressBar
