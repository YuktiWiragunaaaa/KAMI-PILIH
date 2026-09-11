import flet as ft


def main(page: ft.Page):
    page.title = "Contoh Glassmorphism Flet"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window_width = 850
    page.window_height = 650
    page.bgcolor = ft.Colors.BLACK

    glass_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("Liquid Glass", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Text("Desain UI di Python", size=18, color=ft.Colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=400,
        height=250,
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        blur=ft.Blur(15, 15, ft.BlurTileMode.MIRROR),
        border=ft.border.all(1.5, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=25,
            color=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
            offset=ft.Offset(0, 8),
        ),
    )

    main_content = ft.Stack(
        [
            ft.Container(
                width=800,
                height=600,
                bgcolor=ft.Colors.BLUE_GREY_900,
                border_radius=30,
                content=ft.Image(
                    src="https://picsum.photos/1000/800",
                    width=800,
                    height=600,
                    fit=ft.ImageFit.COVER,
                ),
            ),
            ft.Container(
                content=glass_card,
                width=800,
                height=600,
                alignment=ft.alignment.center,
            )
        ],
        width=800,
        height=600,
    )

    page.add(main_content)


ft.app(target=main)
