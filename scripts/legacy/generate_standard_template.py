import sys as _sys
if "--i-know-this-overwrites-data" not in _sys.argv:
    _sys.exit("Legacy script, disabled: it builds the old TRAY_YA_1_2 tray and overwrites data/classes_ya1_2_70_tools.json. "
              "See scripts/legacy/README.md. Pass --i-know-this-overwrites-data to run it anyway.")

import json
import base64
import zlib
import numpy as np
import cv2
import os

raw_user_json = """{
    "boxes": [
        {"id": "4X", "type": "mask", "label": "wrench", "x": "425.5", "y": "129", "width": "699", "height": "92", "area": "18778", "mask": "eJwLT0swsosPNLRzMvQz8jf0h5AGBoYGOIE/PkkDQz+QLNgIKEbh+Rsi8YAQYhoSbYAhgk0FxACQENwCCAVloXBgYiD1Bigi2Fk4vI3P11TWScgt1FNFqtuIs5NU1cS6Aq86uCRxptFfFXmAtBCnB6Cui/DnRVgWNgAXFgaQkgmVbQAvktDYEARmw8xDiSioKLbIQxJD8i0WlWiFIbw4gpZzCBEQNPIz8jX2A9HmnrbOGUmRaQYAIwkWyA=="},
        {"id": "4Y", "type": "mask", "label": "wrench", "x": "381", "y": "181", "width": "602", "height": "80", "area": "11936", "mask": "eJxLzk8xMksPNLR2NfMy9Df0MzKAAH9DAxwAp4yhP0gOSELYEBKMwBCoEygCNwXOBJsHNRSszh+iG8SAGwwRgQjAJWDicB6mg7A5kjgRbJqxC1JFFhvAHQcUGUuqDdSxDnegEgD43UhlWcq8Rz9g6I/OoMggKAnLlSDKH5UFloFkYlh+hbFA2drPCJzJoYaiBiwBHs4sjOBBSxA4NPC3cUkNjck0AAC55fBn"},
        {"id": "4Z", "type": "mask", "label": "wrench", "x": "348.5", "y": "230", "width": "531", "height": "70", "area": "8847", "mask": "eJwLDs8wMs0INLRyN/Uy9Dc0MABjA0MwjQkM/TCFgdqA0MDfCEJD+GAzDAygFCofbDRIIZT0N4BogJpmABGDsZEtwuYkUsVxqcbuYUwZiBfRzcGuG5eZ6OIIs/CzBg4guQG/cyiRJQBQQw2aoLDL4YxL7IBEZxEwnijTDMGpHpELQGxQ1oBlECgNRQZIIpAcBRYB6/czQtiHOxgwEzFxfHBu9jPys3YNjEjJNgAAR1/V3A=="},
        {"id": "4a", "type": "mask", "label": "wrench", "x": "324.5", "y": "274.5", "width": "471", "height": "61", "area": "6532", "mask": "eJwLS8kzso8LNDQ0AAJ/DBIKgBxDfwTX0B/EQyGBaoCEPwzBeSAZA7ACf5ARhgYQLVCeP8Q0mKkGyFYYkAXI1Ue0Tgxl9HYpzX1INX0oSYgEQ/HqI9c+IqzGKg5OsQhpRNo1QEvy/igJHiOD+BlhMR3DxVi84G+EltsS42NzDQB1vb1F"},
        {"id": "4b", "type": "mask", "label": "wrench", "x": "302.5", "y": "313", "width": "435", "height": "52", "area": "4378", "mask": "eJzLj80yMksKNDT3M/I39DfwNzQAYzAJYeAC/mANBhAMJoFiQAKMIRScjS4KBoYwBoTnDyPgFBqTFoBC42nsOuIBDodgChMjggnwpwSq6QI7hThduFyNXRxFFJoYEQwMjClkYIiGifeTn7EvBKZkp+cZAADCcq7s"},
        {"id": "4c", "type": "mask", "label": "wrench", "x": "275.5", "y": "351", "width": "377", "height": "42", "area": "3893", "mask": "eJwLSM4xMsoONDT2NfE18jP0NzAw8Dc0QAZgLrIYSBGQ6w8kkFmGIEVQJhoPbCwugFeSICBJN4ZiOto9qHRDoo62AJRkgDFviJGgsLjGH8k/iCQDSUBYkhci8WEmLbhlaLaCDQRhXyNfE5+o8OQAQwDp0Ze0"},
        {"id": "4d", "type": "mask", "label": "wrench", "x": "275", "y": "403.5", "width": "374", "height": "45", "area": "3531", "mask": "eJyLTcs1sk4ONDQgExga+IP0+gMZEALEhzDAFJKsIRQhq4NoMwBrgQigAH+C7iKkAos8mhCci90oqJvxmYIij0sxLodCxXE5Cr8yOrkSVxAR5UpDRARD2FARCM8QnkxwsDFkQDoNUJMKUNwQLen4G6K529Df2NfYx8QnMjI1wBAA7kSZqg=="},
        {"id": "4e", "type": "mask", "label": "wrench", "x": "320.5", "y": "466.5", "width": "487", "height": "35", "area": "7780", "mask": "eJxLCk4ysk4KNDT0B0MDIICQaCwjfwPcwBCfJD1UIxw60sCozwcWoCVPaA4C5xaYA6E8SA4y9ENSYWBo4A8xwxBBQ5gGEHOhNFQdimqg8UAabAmENvIx9jYFwpigyFwDAAOxv9o="},
        {"id": "4f", "type": "mask", "label": "wrench", "x": "289.5", "y": "499.5", "width": "407", "height": "27", "area": "5234", "mask": "eJyLSMs2Mk4LNDT1M/Y3AANDNJq+wN9wIGylMcDw1LD0JQagoy9hVgFpYLoF82A0kOWHRvtDEjcSjUZA076hgT/MUD8QNvYx9jbzzo5KyTcAAEgLoFE="},
        {"id": "4g", "type": "mask", "label": "wrench", "x": "267.5", "y": "530", "width": "361", "height": "20", "area": "4278", "mask": "eJwLzswxMksONDQ1AAFDfwMkgMqjLfA3pJ9dtAXDxyd08wvYGnBqg1oIZMOtNvSDsoCC0BQJY8G4Bv5QY/yNgBqNfE29ggJDAg0B9dmNoQ=="},
        {"id": "4h", "type": "mask", "label": "wrench", "x": "248", "y": "563", "width": "316", "height": "16", "area": "3238", "mask": "eJzLzs83skgLNDQAA0N/AySAj0dt4G9IS9PJBDgdNShdixPQzLVQg6EpA24NmI/gGfgjCcO5hn6GfvGJCUGGALiafE0="},
        {"id": "4i", "type": "mask", "label": "wrench", "x": "222.5", "y": "591.5", "width": "263", "height": "13", "area": "2333", "mask": "eJzLCAo0NskMNDQ0MPQ38AeTQIBMEgOAGsmQItNEMsEQdyNOSeyxRJKoAVTY0M/I18QnIjU8xBAAxUtohg=="},
        {"id": "4j", "type": "mask", "label": "wrench", "x": "189.5", "y": "621", "width": "203", "height": "12", "area": "1461", "mask": "eJzLzc01MsoONDTyNwACQzCJE/gb4pUmAVBgEoZW6rmK6j7EHp5oonCuoQGUZehn6G/sGx0XFWYIAHfTUaM="},
        {"id": "4k", "type": "mask", "label": "wrench", "x": "193.5", "y": "649.5", "width": "201", "height": "13", "area": "1449", "mask": "eJxLjAg2NsoONDQ0gABDfwN/GBsN4BLHLYNbB9UAHaygBECcByeBoWsAIUDA0ADGAolBhP2NfI18jf3Sw8PDDAHnRFEK"},
        {"id": "4l", "type": "mask", "label": "wrench", "x": "219.5", "y": "690", "width": "265", "height": "14", "area": "2278", "mask": "eJwLzMsxskgLNDQwMPQ3gAIEi3jgb0i6HjqbjseQwe16QvGBQx5uLVQexRlADgQhpIDKgLShv5GviW9eamSIIQCrUGmf"},
        {"id": "4m", "type": "mask", "label": "wrench", "x": "200.5", "y": "717.5", "width": "213", "height": "9", "area": "1345", "mask": "eJxLjgkxNsoKNDQygABDfwNk4G9oQCJA0kGUZopsoJEGYgFaYNHcHUZ+UTGZoYYAi1VUnA=="},
        {"id": "4n", "type": "mask", "label": "wrench", "x": "311.5", "y": "762.5", "width": "423", "height": "55", "area": "6963", "mask": "eJzLzowyNs4MNDT2N4RDA/oAf0MwRTf7Bgb4G9Hdf8AQBcaikZ+hgaEfKD6BLgDx/CF8I5isr7G3qbeprzHUnYYorobyjH3NPM09Tb2N/Yx8TXyM/Qz9wMbSL5EQAqjOHmBg6GcCDNKgiJQ8AwCoC6hc"},
        {"id": "4o", "type": "mask", "label": "wrench", "x": "339", "y": "941", "width": "378", "height": "68", "area": "11140", "mask": "eJyNUUEOwyAM+xJJKXsDXSHqbaddp2nS+v/bBBSaEtBAFRDbwXLz2nc9fTYwi1kmp8oiCF+9GtCJMxLoekoEfPups+OfcUcp1D1dFpGCjkWz85BJjpCq/QiZ9mI3ZtPjhqINc2w+nuWKJvkmJhbCJTzekAJTVRJJPeGNfJbfVLk3ah6c6nHB1TaasYrQo0NCp51e9X1eZ2vszT7ez6/6Ab6cnsM="},
        {"id": "4p", "type": "mask", "label": "wrench", "x": "982", "y": "939.5", "width": "636", "height": "47", "area": "17148", "mask": "eJzLCg5MM7COCDS08TMCQX9DIDQAAn9DEGkA4cB4UADngWVR5ZA0QSkMGUwNQBEMxagOQLMYj1lAMSPyzMJwKFYZFI2oVqHIoDoMyRhcPsXhVoSsoZ8hlARKQoIMYj+YRMhiDRRcrsEGCOqnCRgYW8myl8pOJRAddATUcQlSUiQmuaKqweYWbPkXZiTcYGDBBSrCjH0hGFiQ+RkZYMtIQBE/I19jIMwKzDEBAMTt/u0="},
        {"id": "4q", "type": "mask", "label": "socket", "x": "145", "y": "860", "width": "140", "height": "54", "area": "6980", "mask": "eJwLj0kwsg0NNLT3MvU28zLxM/IzNDD0M/I38Dc0AAIQCWEZGBj6GxjgZsFUEWKh68MpBuQSoQoDoNtEnmqgLc52Yf5J2VkRhgCh6DvM"},
        {"id": "4r", "type": "mask", "label": "socket", "x": "306.5", "y": "860.5", "width": "135", "height": "49", "area": "6129", "mask": "eJzLjMwzTzUICTQ08zLzNfYzgkF/Q38D7MDfEIcEXoBfF8wyXDS17cMBvE1dbVxsXPLCkoINAfT1OQc="},
        {"id": "4s", "type": "mask", "label": "socket", "x": "465", "y": "858", "width": "132", "height": "46", "area": "5409", "mask": "eJzLzg+3NY8LNLR1t/Ax9Tb1NvYzwA4M/XFIgIG/ITKNysOkUU0jzMalghiAsBOvIpAy//i06DwDAG1WN/w="},
        {"id": "4t", "type": "mask", "label": "socket", "x": "570", "y": "713", "width": "270", "height": "32", "area": "4666", "mask": "eJwLD4yzM4sONLT3MPc3BEMD4oC/ITqDMEAYbugHssrIz8jf0M8IyDaCWk609aRbTgZAMp0GFlFqJN6wghuOoQqrtVBVSHLAuPAz9jXyi4pMzjAAAEnnbSI="},
        {"id": "4u", "type": "mask", "label": "socket", "x": "510.5", "y": "651.5", "width": "149", "height": "35", "area": "3695", "mask": "eJxLC4i3yzAIDTQ09jXyM/I3BEMDGPA3NCAIDP3wKUIyDCHibwTUA9TnD7QQyiLCIhIAlY0DGwkOHr/85KQcAwB7Iz7D"},
        {"id": "4v", "type": "mask", "label": "socket", "x": "506", "y": "592", "width": "138", "height": "32", "area": "2933", "mask": "eJzLCkiwSzMIDzQ08jf0M/IDkYYGhv4GGMDfEIWLqQQugqQSSRVIFIyN/BFsCMZmHYYYSB9ZAM3hOIRQ7QbB0MjcHAMAz787MA=="},
        {"id": "4w", "type": "mask", "label": "screwdriver", "x": "950", "y": "182.5", "width": "150", "height": "79", "area": "7306", "mask": "eJxLCwnINbCODzRMN4j0t3U29THxM/I19jOCkX6GBgb+QAwCUNrQH10EFwCqBCJMANdm6GfkDzIOZBGQ5WfoDyJBlhr6QcTAclAxiIlwEqTdEEXM3xDsaGMfM2+gR8DQ2NfQ3xBZD5JuVBriWBAHZCzUUBgLaAbEGCNfM+/k2AA7ANl8RYU="},
        {"id": "4z", "type": "mask", "label": "screwdriver", "x": "1124", "y": "135", "width": "252", "height": "26", "area": "2886", "mask": "eJyLSwwKNEwwiAs0NPQ39DfyQ5AGBv6GBiQBPOpBxkFUGPoZ+RlDLSCkD6zG38AQpMQfRgLFgGYg9PiDTDQi1a3EOnzYAmDY+hv5ZmYnmgEA1oFmvQ=="},
        {"id": "51", "type": "mask", "label": "screwdriver", "x": "1142", "y": "177.5", "width": "168", "height": "81", "area": "8013", "mask": "eJxtT0EKAjEM/FInLSw+QWw76B5ERG9e/P8DTHZDjdJA6WQynUlf18sKvM8oTYgEJitFseas1w/ryshSurSsRxP0zvWLpSfsUovu+I9Qt2EIqsC8uDl2eyDGEKFDSJ/s4t2Y+GwImMLanKJ9W25hHi49N/tkOZVa6nI8PPm43ZcPW1lMrg=="},
        {"id": "52", "type": "mask", "label": "screwdriver", "x": "1127", "y": "273", "width": "358", "height": "62", "area": "13498", "mask": "eJylUcsOAiEM/KUWiH/gbbcTj2bjcY03//8msDxqWV+xJLSUzkCny3q50+F2YiIGITrKUTEWrtGWQz03U5kSjjVf2x/Qnxhah3DCCQKGax3a/mOFOHFzmNPuxU8++4KlCq2U6tRFLY/CCKo0RvdGbbAG7JGomyFnvjHYZ8kM5QvA3sNvqzrPED19uLcrTYhNZcQxxBWmPJTkj+flGh6DOJQR"},
        {"id": "53", "type": "mask", "label": "screwdriver", "x": "860", "y": "312.5", "width": "350", "height": "61", "area": "12986", "mask": "eJzLykhLM7CIDzS08jL3NPMy9zbxMfY19AdBI38DCPA3NDCEscHA0M8QmecPUoHEg+pB4qHKYeXRGyA5GYUN5ME9juRRmCcR3jPEogrFLJgCFBqiEaQIZA3ESKB2fyM/YID7wUhjXxAERQVQxM8IEZwQmyA8sDtBIsDI8kOPIrLCgSCgKMpIsgnFVmRfG8DjAeh/EJmQlmoLAJgFkKY="},
        {"id": "54", "type": "mask", "label": "screwdriver", "x": "1085", "y": "360", "width": "438", "height": "64", "area": "16084", "mask": "eJwLy0zLMTDODDQ0MjD0MzQwgJH+Bv4gmkxAid7BbhuJ9gFDEpnnB9frb+SPMA2sCm4uWJW/ob+xr5GvsZ+Rn5GviS+IBLGNfcAifkb+YANQIg01Akl1G9xFhHnI/sDgGaCHEC3jhyh/4gZ4nYZkNlAdWkQiRR40cCBq4LECxP6gKANFoomvsQ8oCo09zV0jYjJMAEhTsVk="},
        {"id": "55", "type": "mask", "label": "screwdriver", "x": "817.5", "y": "407", "width": "435", "height": "66", "area": "16258", "mask": "eJy9UkEOhCAM/FJb8WLWFyzQ6NWLiTF78f9nBRSLsnoxlhDKdKCFafubBqi6Bj9afct1KoOWmCyCN0ZAhmi44c5nF43+ygbJZ5Jnhf+8Md5zLsrIoQkmnypz7U/OowdcfIjHE2IIprs9YcCDAotAi0iGbKGVLkyYyhC78FZNusbrhLQv2rvZrnJmUdnY/5gZPU/cQx/533ejH8Z6BnMYsU4="},
        {"id": "56", "type": "mask", "label": "screwdriver", "x": "1019", "y": "464", "width": "590", "height": "70", "area": "22787", "mask": "eJzNVFEOwiAMvRItaNwJZjKg7sv4oV+aeP8TSGGs6zTZfkx4BDLe0tfyaLjeLm/TPUcAA2SorgllbQNN1JKcaQVN+JFBQFg6hjByVdUliKXGvCcMmKbzaQQ3OG+DjRyZ/oLJESwzHUxaEGlKIlwVLpxZ5BBPYA5T+5lTN/nNSGJRjNrxrYxr/Q1mL/7dgj/0d5Wv7dHm6Ael3h4bzN/y6HAbITdFntYfhmN/Onf943V3H3yP7Fg="},
        {"id": "57", "type": "mask", "label": "screwdriver", "x": "889.5", "y": "527.5", "width": "575", "height": "67", "area": "21335", "mask": "eJzLzMtLNrANDTRMMPA08zb1MvMx9jX0NzQw9DM0MPAHs/wNQADBAgKwLISFTdYfxEeSh/OGPUAEAhYRcDAgAgwujxo8/kYEdCAHP3Yd+JwFMdIPlYQ4AkSCjQKS/kZ+Rr4mPia+QNLX2MfYD4x9jZCUGCCi3R/JCHTeKBjs4YAtzdBEDBIOcBKcQgyBKS0pJ88CAGcd5u0="},
        {"id": "58", "type": "mask", "label": "screwdriver", "x": "1006.5", "y": "594", "width": "595", "height": "46", "area": "9684", "mask": "eJyLTEhINzDKDDQ08TUyMPQ3GAW0BiQFsr8hzdwxMgGpAYqhHhR9YOxn6G8ExkYQHjRiQSyITiNYRMNYmCLILFQrcDsVR/qBqsYmi2IH3H3obH+EhWhsdMPhckAGqiNRBeBuAYuhugzZChwqwUFrCMF+Rr5WLqkhGSYAJGvq0g=="},
        {"id": "59", "type": "mask", "label": "screwdriver", "x": "852", "y": "629.5", "width": "492", "height": "43", "area": "8982", "mask": "eJxLjwxOMbCMCTS08THxMfIzNDDwN/I3AJJAloGhP4QGsvzANJBn6G8ABXAWRAeqGBobZiImgFmEBLDyYA7xRzIIyWIkp8HloY7GZqmRPw4ZFIBiGaqbYW6E2WGIHGgoVsAMAdP+xn6GfkZ+Rv5AfShGgzk4ggiPBBGy5AJDooKIXmDUNSTZCkxpRv5GvvFJSdYAlGDENQ=="},
        {"id": "5A", "type": "mask", "label": "socket", "x": "1354.5", "y": "229", "width": "79", "height": "72", "area": "4290", "mask": "eJxtjbEOgDAIRH/pjtYvcKUlOjjoppP6/7ulrYmDgYOXI8B97RsPrBODRo0pVIUkJq5MI5gJmBicW/06lUHnnnCnItoYfRU/npUX5RSzeLw9hSLJUQeN4zKffACP9Chc"},
        {"id": "5B", "type": "mask", "label": "socket", "x": "1354.5", "y": "308", "width": "77", "height": "66", "area": "3793", "mask": "eJyLz0+ONjRNDjS09LDwNPcx9jXyA0JfY39DPyMoNjQAYQN/I38Df2xsA0MQG0TBaRADTkKUwXlgjf4gI4AkWM4QZomfMchqXxMfE19jHyDpY+UeHJhlCAClbSas"},
        {"id": "5C", "type": "mask", "label": "socket", "x": "1354.5", "y": "383", "width": "71", "height": "58", "area": "3235", "mask": "eJxLCE+PNrSKDjS08TH2MfUx8jX2M/Iz9DfyN/QzNDCEkH5Anr+BP4Q0NDAw8DcAkmAWiIQgOBsJIPOA2kGUIYSEGm6EAk18zDzN3S094kNyDQHCTiOJ"},
        {"id": "5D", "type": "mask", "label": "socket", "x": "1354.5", "y": "453.5", "width": "67", "height": "53", "area": "2710", "mask": "eJxLis2MNjRPDDS09DEBQiM/I18jfyM/QyAGkn7G/gYGhv4G/kYQ2sDQD8YCAn9DEDKAsZEJNGlDf0M/QxAJof3gFoBJIx9TbwsPC4+IsHxDAMGLIhA="},
        {"id": "5E", "type": "mask", "label": "socket", "x": "1354.5", "y": "521", "width": "53", "height": "44", "area": "1860", "mask": "eJyLzg2IMTRNDDS09DL3NfY18gNhIz9DfyA2MPQ38DfyNwDRBgb+hgZQAGeBxcEEAoA0+BuCIdgof0M/mKFG3qZuQUlhRgBSExtp"},
        {"id": "5F", "type": "mask", "label": "socket", "x": "1355.5", "y": "585.5", "width": "47", "height": "39", "area": "1521", "mask": "eJzLCAuNMbRKDDS0djfyA0N/QyhtYGAIxDCAzMYiCmT4G4Gwn6E/1CA/Y18w9shKjjACAAOXGGE="},
        {"id": "5G", "type": "mask", "label": "socket", "x": "1356", "y": "646.5", "width": "48", "height": "39", "area": "1491", "mask": "eJxLjQiNMTTNDDS0dDP1NvIz8jP0h2Aw6W/ob2BgiETiBCBpsBKwVrB2P2Moy8I9JT7cCABavBla"},
        {"id": "5H", "type": "mask", "label": "socket", "x": "1360.5", "y": "707.5", "width": "33", "height": "35", "area": "853", "mask": "eJxLDUyKMTTOCjQ08zL1NvM28TH1NvIz9AdDA38DEAAyoMDfCCxhYGDoB2IB+b7GQGjiY+6ZmBxlBADefxLk"},
        {"id": "5I", "type": "mask", "label": "socket", "x": "1309.5", "y": "707", "width": "73", "height": "50", "area": "2751", "mask": "eJwLzAiLMjRNCzQ08TP2NfYz9DP2M/M09wSy/GHQAAgM/QwNIADCh7Kgkgb+MAkIEyGFpsPAH0UMZDyQNPY18jf0M/JDJrPio40BA3sjoQ=="},
        {"id": "5J", "type": "mask", "label": "socket", "x": "1247", "y": "707", "width": "60", "height": "42", "area": "1913", "mask": "eJzLiI6OMDTKDDQ09TH1MvU19jP2NQKSRkDa0N8ACAz9DA1gACjiD+cZGvgjhCFqIRSCi1Dkb+hvBDTIEGywkb+RL5D2MnVPTk0xBQC3qh3x"},
        {"id": "5K", "type": "mask", "label": "socket", "x": "1192", "y": "707.5", "width": "56", "height": "41", "area": "1669", "mask": "eJwLC00OMzTOCDS08DD1NfIDQ39DJNrQwNAfhEAAiWWASiMYCCmgVhAJNMbfEGEoyEi/rOBEcwDsIBx5"},
        {"id": "5L", "type": "mask", "label": "socket", "x": "1135.5", "y": "706", "width": "51", "height": "38", "area": "1488", "mask": "eJxLzskMMbSICzS09DOCQV9jf0MwNDAAYSDwN4SxEAAoYGgAVwRXjhDzN/I39DP0NwJjIz8Lj7zUeEsA88ga2A=="},
        {"id": "5M", "type": "mask", "label": "socket", "x": "1071", "y": "701", "width": "50", "height": "46", "area": "1790", "mask": "eJyLC0gLMrSMDjS09jfyNfLDgP6GYGiABjBEDKHKDfzBmqA8kJHGvsZ+Rr4WHoEpKdYAvUAaWw=="},
        {"id": "5N", "type": "mask", "label": "socket", "x": "1006", "y": "701.5", "width": "44", "height": "45", "area": "1599", "mask": "eJwLjEgJMEw1iAw0NPQzwoT+hv4GBiCMDND5/kBlWDSbe1q7pqfn2AIArcAX5Q=="},
        {"id": "5O", "type": "mask", "label": "socket", "x": "944", "y": "701", "width": "46", "height": "46", "area": "1654", "mask": "eJwLikvMM0g0iAo0NPEzgkF/Q3Ta3wAZoHGBfEOEYiRo6GfmYekRGpdrDwAmWRkM"},
        {"id": "5P", "type": "mask", "label": "socket", "x": "874", "y": "695.5", "width": "60", "height": "59", "area": "2779", "mask": "eJwLzszPNjCLCTS09bD0NfJDgr7G/oZ+Rv6GEBKIDfwNDYAASBr6G0AAnAHnQEVASv1BWkBagRrARhr7Ag0FkX7GPsZ+5p42LiERAUkGADvXH4Q="},
        {"id": "5Q", "type": "mask", "label": "socket", "x": "802.5", "y": "701.5", "width": "45", "height": "45", "area": "1677", "mask": "eJzLzcnONLBMCjS0cTXxNfKDQn9DKMvQAAIM/Q0wAJKYIUiLP5wEQV9jP0M/W5ewwJQUAwDhyRgs"},
        {"id": "5R", "type": "mask", "label": "socket", "x": "742", "y": "704.5", "width": "42", "height": "41", "area": "1333", "mask": "eJzLicpNNzBLCjQ09zP2NULBRn6G/ob+Rv4GUGAIYxkaQFlAaUMQaWAIVGzkDyeB2MYlLDM1zQAAa8EXVA=="},
        {"id": "5S", "type": "mask", "label": "socket", "x": "1319.5", "y": "781", "width": "105", "height": "84", "area": "6739", "mask": "eJxdjrEOwyAMRH/JB2Xp1ClDSjgydEhVhZ0M+f8tGASRKsz54TvJ/Pb4hc0rHt693ey8+5whMUZsCCaAhqVTBARFX8qhd4g6RaiZyq0Ewu41rIb8pYYpIzykzXQF0Rd0Ypuikn60nMUuVvW+0/OVj2QuRRs1Ww=="},
        {"id": "5T", "type": "mask", "label": "socket", "x": "1227", "y": "779", "width": "88", "height": "76", "area": "5014", "mask": "eJxNTkEKwCAM+1KrbugHNkFn2MnDPiBj7P/H1algS5o2LaHPlTObcrL1brd+DSrpY0BHDQYnJgZBgSTmiScQ06wQWiu19/1scF2MWSx/Q3QWRaFCyRs15ZHGwUQT3Vbee/kAIKssCA=="},
        {"id": "5U", "type": "mask", "label": "socket", "x": "1144.5", "y": "778.5", "width": "77", "height": "71", "area": "4118", "mask": "eJxLS0sNMTRNDzS0drNyNfMy9jNCQF9jf0MQ9DOC0ECWoYGhvwEI+xtBaAO4mAFUAMEC80AkQgSoGK4FYgRMxB9iqbEvHPuaeJg7pUdmWAAAx+8nGg=="},
        {"id": "5V", "type": "mask", "label": "socket", "x": "1068", "y": "778.5", "width": "76", "height": "71", "area": "4014", "mask": "eJyLCw4NMrRNCDS0dTL2M/IFYhjpZ+Rv6G/gDyTBLDCJYEFkDPwNDAzAJIgwhCEwNoCzUHlwlr+RH9AwoDEglhHEeCA09DPxNvMCQUv3qLxIawCS2ycz"},
        {"id": "5W", "type": "mask", "label": "socket", "x": "991.5", "y": "777.5", "width": "63", "height": "63", "area": "2987", "mask": "eJzLzc7KNzDJCDS0dLd0N/M28jX2M4JAf0Nk2t8QCA0MQKShn6EBiG1gABExMDTwh3LgQnAWRAOKQVCegb+Rn5mnpZu1a35eoB0AEA0hew=="},
        {"id": "5X", "type": "mask", "label": "socket", "x": "919.5", "y": "777", "width": "51", "height": "50", "area": "1944", "mask": "eJwLyknJNbBMCTS0cjP2NfKDQTjb19jfAAgMwSQqC4ltaGDgbwiCfkYwEmqQoZ+Jr7GviQ8QuyWkpSQYAAAcNxtj"},
        {"id": "5Y", "type": "mask", "label": "socket", "x": "854", "y": "778", "width": "48", "height": "52", "area": "1948", "mask": "eJwLDEjMNrBOCjS0cTHywwr9DYHQAAggJASgsYFKQAr9DP3hmoCksS8ImniYuyZkZCcZAACEexoq"},
        {"id": "5Z", "type": "mask", "label": "socket", "x": "783", "y": "775", "width": "46", "height": "48", "area": "1656", "mask": "eJyLzQjLNLBKDjS0cTHyM/Iz9jH2MwJDQ38jfwMDQz9DA0MQ7W8A5hsY+BtCCDBt6A+RgNN+Rr5G/ka+xr7GQKPMvIDQOzU4ItUAADjlGak="},
        {"id": "5a", "type": "mask", "label": "socket", "x": "710", "y": "774.5", "width": "46", "height": "47", "area": "1613", "mask": "eJwLis5MMzDJDDQ097DwMPUx8jX2M/I18jfyM/I3BGIDA0N/QygLBPwNDA0MUJkIBUDSD2SAoT/YGCDbzNvKLTgxNd0AACRiGSw="},
        {"id": "5b", "type": "mask", "label": "socket", "x": "790", "y": "866", "width": "316", "height": "32", "area": "7309", "mask": "eJxLCM5PMbCICzS09DPyM/I3GAbA0B8fd2gCfJ4Ayvkb4teFRR7FRDR5LLZBVeB0B5oJSFxMLTAH2zhlxSYmGAAAtPZ9HQ=="},
        {"id": "5c", "type": "mask", "label": "socket", "x": "1046.5", "y": "867.5", "width": "155", "height": "33", "area": "3782", "mask": "eJyLTwgJMLQPDDS09zcEQwNsAIcwAvgbYmcDeUb+xKjCIYOsG10PQYDH1QRNIuRjUFDlZaRZAQDMdUBb"},
        {"id": "5d", "type": "mask", "label": "socket", "x": "1202.5", "y": "867", "width": "97", "height": "34", "area": "2616", "mask": "eJxLSIsIM7RLCDS0dzT0B0EDCPA3MDRAA/7oIkABDDFkEYRhmKqM/NGFEKpw6gPy0eT8jfwMgdjIIyQ4wQwAPhsqzA=="},
        {"id": "5e", "type": "mask", "label": "socket", "x": "1327.5", "y": "866.5", "width": "93", "height": "37", "area": "3045", "mask": "eJwLio2PMrSMCDRMMHCz8jXyM6AQ+BtSaIChPxD6GfkZ+huBaSN/A5AIxHADQyR1BiAV/kkpsUYAvxkpLw=="},
        {"id": "5g", "type": "mask", "label": "socket", "x": "624", "y": "774.5", "width": "68", "height": "69", "area": "3947", "mask": "eJzLjUtKNsg1CAg0NPI18TXyNfYz9oFgIyA0NDD0M/I38IewYDxDA5zA0B+rMEiLv5E/1DAQ7WfobwS2AmylLxi6WcX7RwaHZhkAAEl+Ivw="},
        {"id": "5f", "type": "mask", "label": "socket", "x": "1369", "y": "767.5", "width": "16", "height": "21", "area": "131", "mask": "eJxLDgmJNTTMDTQ09DfyM/QHkv4GQJYREJv4+Bn5mviYepv4JiVGGQEA9cALWA=="}
    ],
    "height": 1086,
    "width": 1448
}"""

data = json.loads(raw_user_json)
boxes = data["boxes"]
w_canvas = int(data["width"])
h_canvas = int(data["height"])

# Function to decode COCO RLE
def decode_coco_rle(counts_str, h, w):
    m = len(counts_str)
    counts = []
    p = 0
    while p < m:
        x = 0
        k = 0
        more = 1
        while more:
            c = ord(counts_str[p]) - 48
            x |= (c & 0x1f) << (5 * k)
            more = c & 0x20
            p += 1
            k += 1
            if not more and (c & 0x10):
                x |= (-1 << (5 * k))
        if len(counts) > 2:
            x += counts[-2]
        counts.append(x)
    mask = np.zeros(h * w, dtype=np.uint8)
    cur = 0
    val = 0
    for cnt in counts:
        mask[cur:cur + cnt] = val
        cur += cnt
        val = 1 - val
    return mask.reshape((w, h)).T

# User image
user_img_path = r"C:\Users\polwa\.gemini\antigravity-ide\brain\e94903e8-e625-4570-b6b1-d9946b7ac04a\.user_uploaded\media_1792342584852.jpg"
orig_img = cv2.imread(user_img_path)
ref_1448 = cv2.resize(orig_img, (w_canvas, h_canvas), interpolation=cv2.INTER_LANCZOS4)

# Create blueprint wireframe
blueprint = np.full((h_canvas, w_canvas, 3), (32, 28, 24), dtype=np.uint8) # Dark blueprint navy background

# Load 70 tools metadata to inherit names if matching
tools_info_path = "mock_database/classes_ya1_2_70_tools.json"
tools_info = []
if os.path.exists(tools_info_path):
    with open(tools_info_path, "r", encoding="utf-8") as f:
        tools_info = json.load(f)

# Sort boxes logically by row (y) then column (x) for clean slot numbers 1..N
sorted_boxes = sorted(boxes, key=lambda b: (round(float(b["y"]) / 50.0), float(b["x"])))

slots = []
for idx, b in enumerate(sorted_boxes, start=1):
    b_id = b["id"]
    label = b["label"]
    cx = float(b["x"])
    cy = float(b["y"])
    bw = float(b["width"])
    bh = float(b["height"])
    
    # decode mask
    rle_str = zlib.decompress(base64.b64decode(b["mask"])).decode('ascii', errors='ignore')
    bin_mask = decode_coco_rle(rle_str, h_canvas, w_canvas)
    
    cnts, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.005 * peri, True)
        polygon = [[float(pt[0][0]), float(pt[0][1])] for pt in approx]
        
        rect = cv2.minAreaRect(c)
        angle = rect[2]
        rw, rh = rect[1]
        if rw < rh:
            angle = (angle + 90.0) % 180.0
    else:
        x1, y1 = cx - bw / 2.0, cy - bh / 2.0
        x2, y2 = cx + bw / 2.0, cy + bh / 2.0
        polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        angle = 0.0
        
    rad = np.radians(angle)
    orient_vec = [round(float(np.cos(rad)), 3), round(float(np.sin(rad)), 3)]
    
    # Coordinates normalized
    x1_px = max(0.0, cx - bw / 2.0)
    y1_px = max(0.0, cy - bh / 2.0)
    x2_px = min(float(w_canvas), cx + bw / 2.0)
    y2_px = min(float(h_canvas), cy + bh / 2.0)
    bbox_norm = [
        round(x1_px / w_canvas, 4),
        round(y1_px / h_canvas, 4),
        round(x2_px / w_canvas, 4),
        round(y2_px / h_canvas, 4),
    ]
    
    # Determine name & part number
    name_th = f"{label.capitalize()} #{idx} ({b_id})"
    part_no = f"TRAY-YA-{idx:02d}"
    if idx <= len(tools_info):
        t_meta = tools_info[idx - 1]
        name_th = t_meta.get("name_th") or t_meta.get("name") or name_th
        part_no = t_meta.get("code") or part_no
        
    # Tolerance
    if label == "socket":
        center_tol = max(12.0, min(bw, bh) * 0.35)
        angle_tol = 35.0
        iou_min = 0.38
    elif label == "wrench":
        center_tol = max(18.0, min(bw, bh) * 0.35)
        angle_tol = 15.0
        iou_min = 0.45
    else:
        center_tol = max(15.0, min(bw, bh) * 0.35)
        angle_tol = 18.0
        iou_min = 0.42
        
    slot_entry = {
        "slot_number": idx,
        "part_number": part_no,
        "name": name_th,
        "code": part_no,
        "class_key": label,
        "code_id": b_id,
        "category": label,
        "expected_class": label,
        "filename": f"{part_no}.png",
        "bbox_norm": bbox_norm,
        "polygon": polygon,
        "tolerance": {
            "center_px": round(center_tol, 1),
            "angle_deg": angle_tol,
            "iou_min": iou_min
        },
        "orientation_vec": orient_vec
    }
    slots.append(slot_entry)
    
    # Draw polygon contour on blueprint wireframe
    poly_pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    # Semi-transparent polygon fill
    color = (0, 230, 255) if label == "wrench" else ((0, 255, 128) if label == "socket" else (255, 180, 0))
    cv2.polylines(blueprint, [poly_pts], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)
    cv2.circle(blueprint, (int(cx), int(cy)), 3, color, -1)
    cv2.putText(blueprint, str(idx), (int(cx) - 8, int(cy) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

# Draw outer border and alignment marks
cv2.rectangle(blueprint, (20, 20), (w_canvas - 20, h_canvas - 20), (0, 220, 255), 2)
# Corner marks
arm = 60
cv2.line(blueprint, (20, 20), (20 + arm, 20), (0, 255, 255), 4)
cv2.line(blueprint, (20, 20), (20, 20 + arm), (0, 255, 255), 4)
cv2.line(blueprint, (w_canvas - 20, 20), (w_canvas - 20 - arm, 20), (0, 255, 255), 4)
cv2.line(blueprint, (w_canvas - 20, 20), (w_canvas - 20, 20 + arm), (0, 255, 255), 4)
cv2.line(blueprint, (20, h_canvas - 20), (20 + arm, h_canvas - 20), (0, 255, 255), 4)
cv2.line(blueprint, (20, h_canvas - 20), (20, h_canvas - 20 - arm), (0, 255, 255), 4)
cv2.line(blueprint, (w_canvas - 20, h_canvas - 20), (w_canvas - 20 - arm, h_canvas - 20), (0, 255, 255), 4)
cv2.line(blueprint, (w_canvas - 20, h_canvas - 20), (w_canvas - 20, h_canvas - 20 - arm), (0, 255, 255), 4)

# Save blueprint images
os.makedirs("admin_data/tray_refs", exist_ok=True)
cv2.imwrite("admin_data/tray_refs/TRAY_YA_1_2.jpg", ref_1448)
cv2.imwrite("admin_data/tray_refs/TRAY_YA_1_2_sketch.png", blueprint)
overlay = cv2.addWeighted(ref_1448, 0.65, blueprint, 0.35, 0)
cv2.imwrite("admin_data/blueprint_overlay_on_ref.jpg", overlay)

# Complete template schema with BOTH 'slots' and 'tools' for full compatibility
template_dict = {
    "tray_id": "TRAY_YA_1_2",
    "tray_name": "ถาดเครื่องมือ YA 1/2 (ครบ 70 ช่อง)",
    "description": "ถาดโฟมเครื่องมือช่าง YA 1/2 พร้อมตำแหน่งและพิกัด Polygon จาก Mask แม่นยำ",
    "version": "2.1.0",
    "image_size": [w_canvas, h_canvas],
    "image_width": w_canvas,
    "image_height": h_canvas,
    "slot_count": len(slots),
    "total_slots": len(slots),
    "reference_image": "admin_data/tray_refs/TRAY_YA_1_2.jpg",
    "sketch_image": "admin_data/tray_refs/TRAY_YA_1_2_sketch.png",
    "slots": slots,
    "tools": slots
}

for out_name in ["TRAY_YA_1_2.json", "tray_ya1_2_70_tools.json"]:
    out_p = os.path.join("mock_database/tray_templates", out_name)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(template_dict, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_p}")

print("Update completed successfully! Slots total:", len(slots))
