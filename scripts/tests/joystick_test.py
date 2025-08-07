# Save this as test_ps4_controller.py and run it in your terminal

import pygame

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick detected. Please connect your PS4 controller.")
else:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Detected controller: {joystick.get_name()}")
    print(f"Number of axes: {joystick.get_numaxes()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")

    print("Move sticks or press buttons (Ctrl+C to exit)...")
    try:
        while True:
            pygame.event.pump()
            for i in range(joystick.get_numaxes()):
                print(f"Axis {i}: {joystick.get_axis(i):.3f}", end=" | ")
            for i in range(joystick.get_numbuttons()):
                print(f"Button {i}: {joystick.get_button(i)}", end=" | ")
            print("\r", end="")
    except KeyboardInterrupt:
        print("\nExiting.")

pygame.quit()