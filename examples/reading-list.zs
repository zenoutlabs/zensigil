# A personal reading plan: put short, unread books on the next-up list.
rule "Choose a next read":
    for book in books:
        when not book.finished and book.pages <= max_pages:
            propose read_next(
                id: book.id,
                title: book.title,
                explanation: book.title + " is unread and has " + text(book.pages) + " pages, within your " + text(max_pages) + "-page limit."
            )
        otherwise:
            say book.title + ": already finished or longer than your page limit."
