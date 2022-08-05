import math
import random

import pygame


def rand_sample_between(min_val, max_val):
    return random.random() * (max_val - min_val) + min_val


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def transform(self, dist, rotation):
        """Return a new Point after moving float dist in the float rotation direction.
        """
        return Point(
            x = dist * math.cos(rotation) + self.x,
            y = dist * math.sin(rotation) + self.y
        )

    def to_tuple(self):
        return (self.x, self.y)


class Color:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def change_magnitude(self, mag):
        mult = max(0, (1 + mag))
        return Color(
            r=Color.cap(self.r * mult),
            g=Color.cap(self.g * mult),
            b=Color.cap(self.b * mult),
            a=self.a
        )

    def to_tuple(self):
        return (self.r, self.g, self.b, self.a)

    @staticmethod
    def cap(val):
        return int(max(0, min(val, 255)))


class Config:
    def __init__(
        self,
        thickness_decay,
        mid_thickness_multiplier,
        branch_color,
        num_child_range,
        child_thickness_multiplier_range,
        min_thickness,
        min_length,
        child_length_decay,
        rotation_range,
        depth_range,
        curve_resolution
    ):
        self.thickness_decay = thickness_decay
        self.mid_thickness_multiplier = mid_thickness_multiplier
        self.branch_color = branch_color
        self.num_child_range = num_child_range
        self.child_thickness_multiplier_range = child_thickness_multiplier_range
        self.min_thickness = min_thickness
        self.min_length = min_length
        self.child_length_decay = child_length_decay
        self.rotation_range = rotation_range
        self.depth_range = depth_range
        self.curve_resolution = curve_resolution


class Circle:
    def __init__(self, origin_x, origin_y, radius):
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.radius = radius

    def get_angle(self, point):
        dx = point.x - self.origin_x
        ang = math.atan((point.y - self.origin_y)/dx)
        if dx < 0:
            ang += math.pi
        return ang

    def sample_points_between(self, p1, p2, resolution):
        ang1 = self.get_angle(p1)
        ang2 = self.get_angle(p2)
        if ang2 < ang1:
            ang2 += math.pi * 2
        dang = ang2 - ang1
        return [self.query(i/resolution * dang + ang1) for i in range(1, resolution)]


    def query(self, angle):
        return (
            self.origin_x + self.radius * math.cos(angle),
            self.origin_y + self.radius * math.sin(angle)
        )

    @staticmethod
    def from_3_points(p1, p2, p3):
        factor_12 = Circle.calculate_factor(p1, p2)
        factor_13 = Circle.calculate_factor(p1, p3)
        dx_ratios = (p1.x - p3.x) / (p1.x - p2.x)
        origin_y = (factor_13 - factor_12 * dx_ratios) / (
            p1.y - p3.y - dx_ratios * (p1.y - p2.y)
        )
        origin_x = (factor_12 - (p1.y - p2.y) * origin_y) / (p1.x - p2.x)
        radius = math.sqrt((p1.x - origin_x) ** 2 + (p1.y - origin_y) ** 2)
        return Circle(origin_x, origin_y, radius)

    @staticmethod
    def calculate_factor(p1, p2):
        return ((p1.x ** 2 - p2.x ** 2) + (p1.y ** 2 - p2.y ** 2)) / 2


class Branch:
    def __init__(self, base_thickness, length, starting_point, rotation, config, depth=0):
        self.base_thickness = base_thickness
        self.length = length
        self.starting_point = starting_point
        self.rotation = rotation
        self.config = config
        self.depth = depth

        # precomputed values
        self.end_thickness = base_thickness * config.thickness_decay
        self.mid_thickness = self.end_thickness * config.mid_thickness_multiplier
        self.end_point = self.starting_point.transform(dist=length, rotation=rotation)

        # recursive child branches
        self.children = []
        self._recurse()

    def render(self, surface):
        # draw branches in the back first, then work way up to front
        todo = sorted(self._breadth_first_collect([]), key=lambda branch: -branch.depth)
        for branch in todo:
            branch._render(surface)

    # PRIVATE

    def _breadth_first_collect(self, result):
        result.append(self)
        for child in self.children:
            child._breadth_first_collect(result)
        return result

    def _render(self, surface):
        """Renders a single branch.
        """
        base_rite = self.starting_point.transform(
            dist=self.base_thickness/2,
            rotation=self.rotation - math.pi/2
        )
        base_left = self.starting_point.transform(
            dist=self.base_thickness/2,
            rotation=self.rotation + math.pi/2
        )

        mid_point = self.starting_point.transform(dist=self.length/2, rotation=self.rotation)
        mid_left = mid_point.transform(
            dist=self.mid_thickness/2,
            rotation=self.rotation + math.pi/2
        )
        mid_rite = mid_point.transform(
            dist=self.mid_thickness/2,
            rotation=self.rotation - math.pi/2
        )

        tail_left = self.end_point.transform(
            dist=self.end_thickness/2,
            rotation=self.rotation + math.pi/2
        )
        tail_rite = self.end_point.transform(
            dist=self.end_thickness/2,
            rotation=self.rotation - math.pi/2
        )

        left_circle = Circle.from_3_points(base_left, mid_left, tail_left)
        rite_circle = Circle.from_3_points(tail_rite, mid_rite, base_rite)

        polygon_points = [
            base_rite.to_tuple(),
            base_left.to_tuple(),
            *left_circle.sample_points_between(base_left, tail_left, self.config.curve_resolution),
            tail_left.to_tuple(),
            tail_rite.to_tuple(),
            *rite_circle.sample_points_between(tail_rite, base_rite, self.config.curve_resolution),
        ]
        pygame.draw.polygon(
            surface,
            self.config.branch_color.change_magnitude(self.depth).to_tuple(),
            polygon_points
        )

    def _recurse(self):
        """Create child branches.
        """
        assert not self.children
        num_children = random.randint(*self.config.num_child_range)
        for child in range(num_children):
            child_thickness = self.end_thickness
            child_length = self.length * rand_sample_between(
                *self.config.child_length_decay
            )
            if child_thickness > self.config.min_thickness and child_length > self.config.min_length:
                child = Branch(
                    base_thickness=child_thickness,
                    length=child_length,
                    starting_point=self.end_point,
                    rotation=rand_sample_between(*self.config.rotation_range) + self.rotation,
                    config=self.config,
                    depth=rand_sample_between(*self.config.depth_range) + self.depth
                )
                self.children.append(child)


def main():
    import time
    #random.seed(1337)

    screen_width = 1200
    screen_height = 800

    color = [
        Color(160, 0, 160, 0),  # purple
        Color(0, 120, 160, 0),  # blue
    ][random.random() > 0.5]

    config = Config(
        thickness_decay=0.8,
        mid_thickness_multiplier=0.8,
        branch_color=color,
        num_child_range=(2, 2),  # force 2 branches in default mode
        child_thickness_multiplier_range=(0.6, 0.75),
        min_thickness=1,
        min_length=10,
        child_length_decay=(0.8, 0.95),
        rotation_range=(-math.pi/6, math.pi/6),
        depth_range=(-0.15, 0.15),
        curve_resolution=20
    )
    root = Branch(
        base_thickness=20,
        length=100,
        starting_point=Point(x=int(screen_width/2), y=0),
        rotation=math.pi/2,
        config=config
    )

    # render the tree on a surface the size of the display
    surface = pygame.Surface((screen_width, screen_height))
    root.render(surface)
    upsided_surface = pygame.transform.flip(surface, False, True)

    # draw the surface onto the display
    screen = pygame.display.set_mode((screen_width, screen_height))
    screen.blit(upsided_surface, (0, 0))
    pygame.display.flip()

    running = True
    while running:
        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                running = False

        time.sleep(0.01)


if __name__ == "__main__":
    main()