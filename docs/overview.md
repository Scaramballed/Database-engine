# NOTE

Hi, I am Scara. Throughout this documentation, I aim to explain the reasoning behind the structure, the code, and the architecture of this database engine project.

More information about why I chose this particular project can be found in the README (if you are curious enough). As of now, I am still very much a beginner, but I am aspiring to become better at Python and computers in general.

Furthermore, the order in which I learned and built the project was an important aspect for me. I started by developing a basic understanding of concepts such as pages, records, and tables, and most importantly, how data can be represented and manipulated at the byte level on disk.

After understanding these concepts, I started building this project. More details about what I learned along the way can be found in the learning log.

## Architecture Behind the Engine

SQL / CLI
    ↓
Tokenizer
    ↓
Parser → AST
    ↓
Query Engine
    ↓
Storage Engine
    ↓
Pages / Records
    ↓
Disk (.db)

The architecture represents the flow of a query through the database engine.

The SQL / CLI layer accepts the user's SQL command, which is broken into tokens by the Tokenizer. The Parser then converts these tokens into an AST (Abstract Syntax Tree) representing the structure of the query.

The Query Engine interprets the AST and determines which operations need to be performed. The Storage Engine is responsible for managing how data is organized into Pages and Records, which are ultimately read from or written to the `.db` file on disk.

In short:

**User query → understand the query → execute the operation → access the stored data → read/write to disk.**

## How would I actually elaborate my lines my codes???

What does this code do?
        ↓
Why do we need it?
        ↓
What concept is it implementing?
        ↓
Why did I choose this approach?
        ↓
What would happen without it?
        ↓
Yea, I would try my best to answer those questions.