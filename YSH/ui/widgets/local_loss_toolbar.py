"""One compact local-loss action row; callbacks and button assets stay owned by pages."""


def layout_local_loss_toolbar(container, buttons, total):
    for column, button in enumerate(buttons):
        container.columnconfigure(column, weight=0)
        button.grid(row=0, column=column, sticky='w', padx=(0 if column == 0 else 8, 0), pady=0)
    container.columnconfigure(len(buttons), weight=1)
    total.grid(row=0, column=len(buttons)+1, sticky='e', padx=(12, 0), pady=0)
