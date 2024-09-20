import numpy as np
import napari
from scipy.ndimage import map_coordinates
import qtpy
from qtpy.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
)
from magicgui import magicgui
import pyqtgraph as pg


def vertices_to_coord(v, spacing):
    """do linear interpolation given vertices
    Returns:
    array of linearly-interpolated coordinates,
    cumulative distance of each coordinate
    """

    segments = []
    for i in range(len(v) - 1):
        sp = v[i]  # start
        ep = v[i + 1]  # end
        # convert to pixel units for all dimensions
        sp_px = sp / spacing
        ep_px = ep / spacing
        dist = np.linalg.norm(ep_px - sp_px)
        npix = int(dist)
        # convert segment back to scale
        segment = np.linspace(sp_px, ep_px, num=npix) * spacing
        segments.append(segment)
    stacked = np.vstack(segments)
    distances = np.linalg.norm(np.diff(stacked, axis=0), axis=1)
    cumulative_dist = np.insert(np.cumsum(distances), 0, 0)
    return stacked, cumulative_dist


class PlotWidget(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        plot_container = QWidget()
        plot_container.setMaximumHeight(340)
        plot_container.setMinimumWidth(250)

        # Create the plot widget
        self.graphics_layout_widget = pg.GraphicsLayoutWidget()
        self.graphics_layout_widget.setBackground(None)

        # instantiate a plot by adding a plot
        self.p = self.graphics_layout_widget.addPlot()

        plot_container.setLayout(QHBoxLayout())
        plot_container.layout().addWidget(self.graphics_layout_widget)

        # Create buttons
        self.create_path_button = QPushButton("Path from points")
        self.update_points_layer_choices_button = QPushButton("^ update ^")
        self.plot_profile_button = QPushButton("plot profiles")

        # Lay out the GUI
        layout = QVBoxLayout()
        self.setLayout(layout)

        buttons_layout = QFormLayout()
        self.points_layers_choices = QComboBox()

        buttons_layout.addRow(
            self.points_layers_choices, self.create_path_button
        )
        buttons_layout.addRow(
            self.update_points_layer_choices_button, self.plot_profile_button
        )

        layout.addWidget(plot_container)
        layout.addLayout(buttons_layout)

        self.create_path_button.clicked.connect(self.create_paths)
        self.update_points_layer_choices_button.clicked.connect(
            self.update_points_layers
        )
        self.plot_profile_button.clicked.connect(self.draw_line_profile)

    def update_points_layers(self):
        self.points_layers_choices.clear()

        current_list = []

        # if there are layers that are not in the list, add them
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Points):
                if layer.name not in current_list:
                    self.points_layers_choices.addItem(layer.name)

    def create_paths(self):
        points_layer_name = self.points_layers_choices.currentText()
        if points_layer_name != "":
            path_name = f"{points_layer_name}::path"
            vertices = self.viewer.layers[points_layer_name].data
            self.viewer.add_shapes(
                vertices,
                name=path_name,
                shape_type="path",
            )

    def draw_line_profile(self):
        # reset plot
        self.p.clear()
        vertices = None
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Shapes):
                vertices = [
                    layer.data[i]
                    for i, t in enumerate(layer.shape_type)
                    if t == "path"
                ]

        # sample intensity for each visible image
        iprofiles = {}
        dists = {}
        colors = {}

        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Image) and layer.visible:
                spacing = layer.scale
                if vertices is not None:
                    for i, v in enumerate(vertices):
                        line_name = f"{layer.name:s}::line_{i:02d}"
                        coords, cdist = vertices_to_coord(v, spacing)
                        intensities = map_coordinates(layer.data, coords.T)
                        layer_color = layer.colormap.colors
                        color = np.asarray(layer_color[-1, 0:3]) * 255
                        iprofiles[line_name] = intensities
                        dists[line_name] = cdist
                        colors[line_name] = color

        for line_name, y in iprofiles.items():
            self.p.plot(
                dists[line_name],
                iprofiles[line_name],
                pen=colors[line_name],
                name=line_name,
                width=1.25,
            )

        self.p.addLegend()
