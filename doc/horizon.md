# Horizon Specification

Horizon file is a simple CSV file containing compas positions in degrees and elevation in degrees (basically Alt-Az representation of the horizon). It marks high/low points on the horizon which determine telescope visibility. A simple example would look as follows:

```
1, 15
2, 19
18, 37
33, 45
66, 67
117, 35
135, 34
160, 10
180, 11
202, 27
238, 35
263, 41
289, 35
314, 41
335, 15
350, 15
360, 15
```

which defines a horizon looking something as follows:

![alt text](/images/doc_70.png "Horizon in Alt-Az")

which will be interpreted with the tool as follows:

![alt text](/images/doc_80.png "Horizon in Alt-Az as polar plot")

It is clear from the above images that the person with the above horizon file needs to move somewhere more suitable to observing as they cannot see much to the west and they really have problems on the east too.

Creating the horizon file is reasonably straight forward. If you have an mobile phone just open the [GyroCom web page](https://rkinnett.github.io/gyrocam/?magdec=0), go out to your observatory and simply record the alt-az using the app. You can then send yourself the CSV file. You will have to edit the generated file but that is simple and you can use notepad (or excel) for it - just remove everything apart from the "Heading" and "Az" columns then save the file under some reasonable name, `horizon.csv` is usually good. Make sure this name is then referenced in the `observatory.yaml` file.
