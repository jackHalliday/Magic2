import scipy as sp
from scipy.spatial import Delaunay
from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt
from . import graphics as m2graphics

# added_points = []


# This class is used to store triangulation data, including the initial
# Delaunay triangulation, points that are used to create it, a list
# of triangles and flat triangles. It's got methods used to retrieve a list
# of all the triangles (for triplot for example) and an optimise function
# that clears up flat fetures
class Triangulation:
    def __init__(self, points, canvas):
        # Store the points and their values
        self.points = points
        self.values = [canvas.fringe_phases[p[0], p[1]] for p in self.points]
        print("Starting triangulation")
        # Calculate the Delaunay triangulation
        self.dt = Delaunay(points)
        # Two lists of Triangle objects, one for all of them and one for
        # the flat ones
        self.triangles = []
        self.flat_triangles = []
        print("Building the data")
        # Create Triangle objects and add them to lists
        for i in range(len(self.dt.simplices)):
            triangle = Triangle(self.dt, i, self.points, self.values)
            if triangle.flat:
                self.flat_triangles.append(i)
            self.triangles.append(triangle)
        print("Finished")
        # Print out some stats
        print(len(self.flat_triangles)/len(self.triangles))
        print(len(self.flat_triangles), len(self.triangles))

    # Get a list of all the triangles. Each elements is a list of three indices
    # pointing to vertices in self.points
    def get_simplices(self):
        return self.dt.simplices

    def optimise(self):
        initial_len = len(self.flat_triangles)
        # This loop will run until no further changes are possible
        changes = 1
        while changes:
            # Set the number of changes to 0. If a change is made, this
            # will be incremented, making the while loop do another round
            changes = 0
            # Instead of using a for loop, we will use a while loop with
            # our own iterator (i). This gives us more control, which
            # is necessary since the list we are iterating on changes size
            # during this operation
            i = 0
            while i < len(self.flat_triangles):
                # Get the flat triangle object in quetsion, as well as its
                # sloped neighbour (if it exists) and the vertex indices
                # for the points that do not lay on the joining edge
                triangle = self.triangles[self.flat_triangles[i]]
                neighbour, op1, op2 = triangle.get_sloped_neighbour(self)
                # If there is no sloped neighbour across a long edge, we leave
                # this flat triangle alone. It is possible that it will get a
                # sloped neighbour later in the loop. If not, the while loop
                # will break due to no changes being made, and this triangle
                # will stay in self.flat_triangles, indicating that it is
                # not fixable
                if neighbour is None:
                    # print("none")
                    i += 1
                else:
                    # Calculate the areas of the two initial triangles, and the
                    # two triangles that would be constructed in an edge flip.
                    # If the sum of the areas before and after the flip is the
                    # same, the simplex formed by the triangles was convex
                    ai1 = 0.5 * abs(
                          (triangle.vert_coordinates[op1, 1] - triangle.vert_coordinates[(op1+2)%3, 1])
                        * (triangle.vert_coordinates[(op1+1)%3, 0] - triangle.vert_coordinates[op1, 0])
                        - (triangle.vert_coordinates[op1, 1] - triangle.vert_coordinates[(op1+1)%3, 1])
                        * (triangle.vert_coordinates[(op1+2)%3, 0] - triangle.vert_coordinates[op1, 0])
                    )
                    ai2 = 0.5 * abs(
                          (neighbour.vert_coordinates[op2, 1] - neighbour.vert_coordinates[(op2+2)%3, 1])
                        * (neighbour.vert_coordinates[(op2+1)%3, 0] - neighbour.vert_coordinates[op2, 0])
                        - (neighbour.vert_coordinates[op2, 1] - neighbour.vert_coordinates[(op2+1)%3, 1])
                        * (neighbour.vert_coordinates[(op2+2)%3, 0] - neighbour.vert_coordinates[op2, 0])
                    )
                    af1 = 0.5 * abs(
                          (triangle.vert_coordinates[op1, 1] - triangle.vert_coordinates[(op1+2)%3, 1])
                        * (neighbour.vert_coordinates[op2, 0] - triangle.vert_coordinates[op1, 0])
                        - (triangle.vert_coordinates[op1, 1] - neighbour.vert_coordinates[op2, 1])
                        * (triangle.vert_coordinates[(op1+2)%3, 0] - triangle.vert_coordinates[op1, 0])
                    )
                    af2 = 0.5 * abs(
                          (triangle.vert_coordinates[op1, 1] - triangle.vert_coordinates[(op1+1)%3, 1])
                        * (neighbour.vert_coordinates[op2, 0] - triangle.vert_coordinates[op1, 0])
                        - (triangle.vert_coordinates[op1, 1] - neighbour.vert_coordinates[op2, 1])
                        * (triangle.vert_coordinates[(op1+1)%3, 0] - triangle.vert_coordinates[op1, 0])
                    )
                    # Check if the areas before and after are the same, and
                    # also whether the final areas aren't zero
                    if ai1 + ai2 == af1 + af2 and af1 != 0 and af2 != 0:
                        # print("convex")
                        self.switch_triangles(triangle, neighbour, op1, op2)
                        del self.flat_triangles[i]
                        changes += 1
                    else:
                        # print("concave")
                        self.add_point(triangle, neighbour, op1, op2)
                        del self.flat_triangles[i]
                        changes += 1
            print(1-len(self.flat_triangles)/initial_len)

    def switch_triangles(self, triangle, neighbour, op1, op2):
        # print("switching", triangle.index, neighbour.index,
        #       "with neighbours", triangle.neighbours,
        #       neighbour.neighbours, self.triangles[29].neighbours)
        tn = triangle.neighbours.copy()
        nn = neighbour.neighbours.copy()
        # This escapes words, maybe a drawing will help?
        # https://imgur.com/ZvuKOZH
        # Basically we need to update the neighbours lists of the
        # triangles we're working with...
        triangle.neighbours[op1] = nn[
            sp.argwhere(neighbour.vertices == triangle.vertices[(op1+1) % 3])
        ]
        triangle.neighbours[(op1+2) % 3] = neighbour.index
        neighbour.neighbours[op2] = tn[(op1+2) % 3]
        neighbour.neighbours[
            sp.argwhere(neighbour.vertices == triangle.vertices[(op1+1) % 3])
        ] = triangle.index
        # ...as well as their neighbouring triangles (if they exist)
        if triangle.neighbours[op1] != -1:
            n_temp = self.triangles[triangle.neighbours[op1]].neighbours
            n_temp[
                sp.argwhere(n_temp == neighbour.index)
            ] = triangle.index
        if neighbour.neighbours[op2] != -1:
            n_temp = self.triangles[neighbour.neighbours[op2]].neighbours
            n_temp[
                sp.argwhere(n_temp == triangle.index)
            ] = neighbour.index
        # Now we just need to update the triangles' vertices
        triangle.vertices[(op1+1) % 3] = neighbour.vertices[op2]
        neighbour.vertices[
            sp.argwhere(neighbour.vertices == triangle.vertices[(op1+2) % 3])
        ] = triangle.vertices[op1]
        triangle.vert_coordinates = self.points[triangle.vertices]
        neighbour.vert_coordinates = self.points[neighbour.vertices]
        # Finally we change the status of the flat triangle,
        # as it is now sloped
        triangle.flat = False

    def add_point(self, triangle, neighbour, op1, op2):
        # The point is added in the middle of the line shared by
        # the two triangles
        new_point = sp.mean([triangle.vert_coordinates[(op1+1) % 3],
                             triangle.vert_coordinates[(op1+2) % 3]], 0)
        # print(triangle.vert_coordinates[(op1+1) % 3],
        #                      triangle.vert_coordinates[(op1+2) % 3], new_point)
        # added_points.append(new_point)
        # The point's value is calculated with a variation on linear
        # interpolation of George's design. It seems to produce
        # reasonable values
        d1 = sp.sqrt(sp.sum((new_point-sp.array(triangle.vert_coordinates[(op1+1)%3]))**2, 0))
        d2 = sp.sqrt(sp.sum((new_point-sp.array(neighbour.vert_coordinates[op2]))**2, 0))
        new_value = (d2*self.values[triangle.vertices[(op1+1) % 3]]
                     + d1*self.values[neighbour.vertices[op2]])/(d1+d2)
        new_index = len(self.points)
        self.points = sp.append(self.points, [new_point], 0)
        self.values = sp.append(self.values, [new_value], 0)
        # Change the triangulation to include the new point
        # A drawing is helpful in understanding what is happening here
        # https://imgur.com/5uUkYz4
        # Start by creating two new, placeholder triangles
        t2 = TriangleCopy(len(self.triangles), self.points,
                          triangle.vertices, triangle.neighbours)
        self.triangles.append(t2)
        n2 = TriangleCopy(len(self.triangles), self.points,
                          neighbour.vertices, neighbour.neighbours)
        self.triangles.append(n2)
        # Now change the neighbours
        triangle.neighbours[(op1+2) % 3] = t2.index
        neighbour.neighbours[
            sp.argwhere(neighbour.vertices == triangle.vertices[(op1+2) % 3])
        ] = n2.index
        t2.neighbours[op1] = n2.index
        t2.neighbours[(op1+1) % 3] = triangle.index
        n2.neighbours[op2] = t2.index
        n2.neighbours[
            sp.argwhere(neighbour.vertices == triangle.vertices[(op1+2) % 3])
        ] = neighbour.index
        if t2.neighbours[(op1+2) % 3] != -1:
            n_temp = self.triangles[t2.neighbours[(op1+2) % 3]].neighbours
            n_temp[
                sp.argwhere(n_temp == triangle.index)
            ] = t2.index
        arg = int(sp.argwhere(neighbour.vertices == triangle.vertices[(op1+2) % 3]))
        if n2.neighbours[arg] != -1:
            n_temp = self.triangles[t2.neighbours[arg]].neighbours
            n_temp[
                sp.argwhere(n_temp == neighbour.index)
            ] = n2.index
        # Now update the vertices
        tv = triangle.vertices.copy()
        triangle.vertices[(op1+1) % 3] = new_index
        neighbour.vertices[
            sp.argwhere(neighbour.vertices == tv[(op1+1) % 3])
        ] = new_index
        t2.vertices[(op1+2) % 3] = new_index
        n2.vertices[
            sp.argwhere(n2.vertices == tv[(op1+2) % 3])
        ] = new_index
        # Finally mark the triangle as sloped
        triangle.flat = False

    def interpolate(self, canvas):
        for triangle in self.triangles:
            co = triangle.vert_coordinates
            div = (co[1,0]-co[2,0])*(co[0,1]-co[2,1])+(co[2,1]-co[1,1])*(co[0,0]-co[2,0])
            a0 = (co[1, 0]-co[2, 0])
            a1 = (co[2, 1]-co[1, 1])
            a2 = (co[2, 0]-co[0, 0])
            a3 = (co[0, 1]-co[2, 1])
            xmin = int(sp.amin(triangle.vert_coordinates[:,1]))
            xmax = int(sp.amax(triangle.vert_coordinates[:,1]))+1
            ymin = int(sp.amin(triangle.vert_coordinates[:,0]))
            ymax = int(sp.amax(triangle.vert_coordinates[:,0]))+1
            for x in range(int(sp.amin(triangle.vert_coordinates[:,1])), int(sp.amax(triangle.vert_coordinates[:,1]))+1):
                for y in range(int(sp.amin(triangle.vert_coordinates[:,0])), int(sp.amax(triangle.vert_coordinates[:,0]))+1):
                    w0 = (a0*(x-co[2,1])+a1*(y-co[2,0]))/div
                    w1 = (a2*(x-co[2,1])+a3*(y-co[2,0]))/div
                    w2 = sp.round_(1-w0-w1, 10)
                    if w0 >= 0 and w1 >= 0 and w2 >= 0:
                        canvas.interpolated[y, x] = (
                            self.values[triangle.vertices[0]]*w0
                            + self.values[triangle.vertices[1]]*w1
                            + self.values[triangle.vertices[2]]*w2
                        )


# Calculate the distance between two points in the points list
def distance(points, i1, i2):
    return sp.sqrt((points[i2, 0]-points[i1, 0])**2
                   + (points[i2, 1]-points[i1, 1])**2)


# A class representing a triangle
class Triangle:
    def __init__(self, dt, index, points, values):
        # Copy the vertex and neighbours info
        self.vertices = dt.simplices[index]
        self.vert_coordinates = points[self.vertices]
        self.neighbours = dt.neighbors[index]
        self.index = index
        # Check whether the triangle is flat
        self.flat = (values[self.vertices[0]] == values[self.vertices[1]]
                     and values[self.vertices[1]] == values[self.vertices[2]])
        if self.flat:
            # If the triangle is flat, it is important to check which of the
            # edges are not parts of the contour - we can flip those without
            # getting lines that cut the contours. The contour lines are always
            # sqrt(2) or shorter
            self.long_edges = [
                distance(points, self.vertices[1], self.vertices[2]) > sp.sqrt(2),
                distance(points, self.vertices[2], self.vertices[0]) > sp.sqrt(2),
                distance(points, self.vertices[0], self.vertices[1]) > sp.sqrt(2)]
            # If none of the edges is longer than sqrt(2), the triangle lies
            # within the contour and it doesn't make sense to fix it.
            self.flat = self.flat and sp.count_nonzero(self.long_edges)
        # This will not be used, but assign a value for consistency
        else:
            self.long_edges = [True, True, True]

    # This function returns the first found sloped neighbour of the triangle.
    # It only checks for neighbours that share one of the long edges, so as
    # to not cut through contours
    def get_sloped_neighbour(self, tri):
        for i in range(3):
            # If the edge is long
            if self.long_edges[i]:
                n_index = self.neighbours[i]
                # If the neighbour exists and isn't flat, return its index
                if n_index != -1 and not tri.triangles[n_index].flat:
                    neighbour = tri.triangles[n_index]
                    return neighbour, i, int(
                        sp.argwhere(neighbour.neighbours == self.index)
                    )
        # If no neighbour found, return None
        return None, None, None


class TriangleCopy(Triangle):
    def __init__(self, index, points, vertices, neighbours):
        self.vertices = vertices.copy()
        self.vert_coordinates = points[self.vertices]
        self.neighbours = neighbours.copy()
        self.index = index
        self.flat = False
        self.long_edges = [True, True, True]


def triangulate(canvas):
    tri = Triangulation(sp.transpose(
                        sp.nonzero(canvas.fringes_image)),
                        canvas)
    plt.imshow(canvas.fringe_phases, cmap=m2graphics.cmap)
    plt.triplot(tri.points[:, 1], tri.points[:, 0], tri.get_simplices())
    plt.triplot(tri.points[:, 1], tri.points[:, 0], [tri.triangles[i].vertices for i in tri.flat_triangles])
    plt.show()
    # plt.triplot(tri.points[:, 1], tri.points[:, 0], tri.dt.simplices)
    print("Optimisation")
    tri.optimise()
    print("Finished")
    plt.imshow(canvas.fringe_phases, cmap=m2graphics.cmap)
    print(tri.flat_triangles)
    # print(added_points)
    # plt.triplot(tri.points[:, 1], tri.points[:, 0], [tri.triangles[i].vertices for i in tri.flat_triangles])
    plt.triplot(tri.points[:, 1], tri.points[:, 0], [triangle.vertices for triangle in tri.triangles])
    plt.triplot(tri.points[:, 1], tri.points[:, 0], [tri.triangles[i].vertices for i in tri.flat_triangles])
    plt.show()
    tri.interpolate(canvas)
    plt.imshow(canvas.interpolated, cmap=m2graphics.cmap)
    # plt.triplot(tri.points[:, 1], tri.points[:, 0], [triangle.vertices for triangle in tri.triangles])
    plt.show()