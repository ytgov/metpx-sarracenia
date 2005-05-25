"""
#############################################################################################
# Name: TextSplitter.py
#
# Author: Daniel Lemay
#
# Date: 2005-05-24
#
# Description: 
#
#############################################################################################

"""
import sys, os, commands, signal

class TextSplitter:
   
    def __init__(self, text, maxSize, alignment="\n", overhead=5):
        self.__text = text                       # Original text (a string)
        self.__maxSize = maxSize                 # Maximum size for each string
        self.__alignment = alignment             # Alignment function (ex: '\r\n')
        self.__overhead = overhead               # Number of overhead character in a text block
        self.__alignmentLength = len(alignment)  # Length of the alignment function
        self.__lines = text.splitlines()         # Original text, splitted in lines (alignment removed)
        self.__blocks = []                       # Final blocks of text that respect the maximum size

    def setText(self, text):
        self.__text = text

    def getText(self):
        return self.__text

    def setMaxSize(self, maxSize):
        self.__maxSize = maxSize

    def getMaxSize(self):
        return self.__maxSize

    def setAlignment(self, alignment):
        self.__alignment = alignment

    def getAlignment(self):
        return self.__alignment

    def setOverhead(self, value):
        self.__overhead = value

    def getOverhead(self):
        return self.__overhead

    def setAlignmentLength(self, length):
        self.__alignmentLength = length
        
    def getAlignmentLength(self):
        return self.__alignmentLength
    
    def setLines(self):
        self.__lines = self.__text.splitlines()

    def getLines(self):
        return self.__lines

    def breakLongLine(self, line):
        """
        Breaks long line in block of text that respect the maximum size for this 
        type of message. An alignment function is added at the end of the
        individual blocks.
        """
        maxLength = self.__maxSize - self.__alignmentLength - self.__overhead
        count = 0
        blocks = []
        newLine = ""

        for char in line:
            if count < maxLength: 
                newLine += char
                count += 1
            else:
                blocks.append(newLine + self.__alignment)
                count = 1
                newLine = char 
        blocks.append(newLine + self.__alignment)

        return blocks

    def breakLongText1(self):
        """
        Will break text in group of maxsize. Contrary to breakLongText, this 
        method will procede correctly in case of line longer than maxSize.
        """

        blocks = []
        count = self.__overhead
        maxLength = self.__maxSize

        for line in self.__lines:
            if len(line) >= self.__maxSize - self.__



        

    def breakLongText(self):
        """
        Will break text in group of maxsize. If a given line is longer than
        maxSize, a problem will result. If this is a situation with which we 
        have to deal, this method will have to be rewritten

        Check breakLongText1 if you need to treat long line

        FIXME: Deal with empty text
        """

        blocks = []
        index = 0
        blocks.insert(index, "")
        count = self.__overhead
        
        for line in self.__lines:
            lineLength = len(line) + self.__alignmentLength
            #print (count + lineLength)
            if (count + lineLength) < self.__maxSize:
                blocks[index] += line + self.__alignment
                count += lineLength
            else: # The block is full. We start with a new block
                index += 1
                blocks.insert(index, "") 
                count = self.__overhead
                #print (count + lineLength)
                if (count + lineLength) < self.__maxSize:
                    blocks[index] += line + self.__alignment
                    count += lineLength
                else: 
                    print "You should never get here. If you are, it's probably because we need to rewrite this method"
                    print "A given line is longer than the maxSize. We don't want to break line, don't we?"
                    self.__blocks = [] 
                    return blocks 

        self.__blocks = blocks 
        return blocks

