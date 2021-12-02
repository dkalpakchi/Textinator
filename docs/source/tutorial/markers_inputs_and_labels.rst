Markers, Inputs & Labels: What's the difference?
================================================

Textinator allows annotating a span of text (or the whole text) with concepts (e.g., Named Entity, Question, Answer, etc.). In order to define a concept, one needs to **define** a *Marker* and specify a name of the concept, a color to be assigned to the span of text, etc. Markers for standard tasks [LINK] in Textinator are pre-defined, whereas if you want to add a custom task, you have to :ref:`define them by hand<custom_annotation_task>`.

When an annotator actually annotates a span of text, then a *Marker* gets **instantiated** into either a *Label* or an *Input*. If a *Marker* has a switched-on flag "Is free text", then it gets instantiated as an *Input*, meaning an annotator is free to write their own input, e.g. a question. If the flag is switched off, it means an annotator can only mark a span inside the text and such *Marker* gets instantiated as a *Label*.