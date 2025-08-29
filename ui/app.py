# ui/app.py
import pygame

class App:
    def __init__(self, width=1280, height=720, title="D20 FC"):
        pygame.init()
        self.flags = pygame.RESIZABLE | pygame.SCALED | pygame.DOUBLEBUF
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

    def run(self):
        while self.running and self.states:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.VIDEORESIZE:
                    # Recreate the window at the new size so the OS maximize works
                    self.screen = pygame.display.set_mode((event.w, event.h), self.flags)
                    # Let the current state recompute its layout
                    st = self.states[-1]
                    if hasattr(st, "handle"):
                        st.handle(event)
                    continue
                # Pass everything else to the current state
                st = self.states[-1]
                if hasattr(st, "handle"):
                    st.handle(event)

            # Update & draw current state
            st = self.states[-1]
            if hasattr(st, "update"):
                st.update(dt)
            if hasattr(st, "draw"):
                st.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
