# ui/app.py
import pygame

class App:
    def __init__(self, width=1280, height=720, title="D20 FC"):
        pygame.init()
        self.flags = pygame.RESIZABLE | pygame.DOUBLEBUF  # <-- no SCALED; we truly resize the surface
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((width, height), self.flags)
        self.clock = pygame.time.Clock()
        self.states = []
        self.running = True

    def push_state(self, st):
        self.states.append(st)
        if hasattr(st, "enter"):
            st.enter()

    def pop_state(self):
        if not self.states:
            return
        st = self.states.pop()
        if hasattr(st, "exit"):
            st.exit()

    def _apply_resize(self, w: int, h: int):
        # Recreate the *actual* backbuffer at the new size
        self.screen = pygame.display.set_mode((w, h), self.flags)
        # Ask the current state to recompute its layout even if it doesn't handle VIDEORESIZE
        if self.states:
            st = self.states[-1]
            if hasattr(st, "_layout"):
                st._layout()
            elif hasattr(st, "handle"):
                # fallback: synthesize a VIDEORESIZE event for states that only listen in handle()
                fake = pygame.event.Event(pygame.VIDEORESIZE, {"w": w, "h": h, "size": (w, h)})
                st.handle(fake)

    def run(self):
        while self.running and self.states:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.VIDEORESIZE:
                    self._apply_resize(event.w, event.h)
                    continue

                st = self.states[-1]
                if hasattr(st, "handle"):
                    st.handle(event)

            st = self.states[-1]
            if hasattr(st, "update"):
                st.update(dt)
            if hasattr(st, "draw"):
                st.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
