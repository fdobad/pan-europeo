# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Marraqueta
                                 A QGIS plugin
 Ponders different rasters with different utility functions
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-05-14
        git sha              : $Format:%H$
        copyright            : (C) 2024 by fdobad@github
        email                : fbadilla@ing.uchile.cl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os.path
import tempfile

import numpy as np
from fire2a.raster import read_raster
from osgeo import gdal, osr
from qgis.core import (Qgis, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsMessageLog, QgsProject,
                       QgsRectangle)
from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Import the code for the dialog
from .pan_batido_dialog import MarraquetaDialog
# Initialize Qt resources from file resources.py
from .resources.resources import *


class Marraqueta:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n", "Marraqueta_{}.qm".format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr("&Pan Europeo")

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("Marraqueta", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ":/plugins/pan_batido/resources/marraqueta.svg"
        self.add_action(
            icon_path, text=self.tr("Load rasters before launching!"), callback=self.run, parent=self.iface.mainWindow()
        )

        self.mc = self.iface.mapCanvas()
        self.mc.scaleChanged.connect(self.handle_scale_change)

        # will be set False in run()
        self.first_start = True

    def handle_scale_change(self, x):
        if layer := self.iface.activeLayer():
            extent = self.iface.mapCanvas().extent()
            xsize = int((extent.xMaximum() - extent.xMinimum()) / layer.rasterUnitsPerPixelX())
            ysize = int((extent.yMinimum() - extent.yMaximum()) / layer.rasterUnitsPerPixelY())
            qprint(f"{xsize=}, {ysize=}")
        qprint(f"zoom scale is {x}")

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr("&Pan Europeo"), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        qprint("current layers", self.iface.mapCanvas().layers())

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            if len(self.iface.mapCanvas().layers()) == 0:
                qprint("No layers loaded. Not loading the dialog!", level=Qgis.Critical)
                # display a message in system toolbar
                self.iface.messageBar().pushMessage(
                    "No layers loaded",
                    "Please load some raster layers before launching the PAN-BATIDO plugin",
                    level=Qgis.Critical,
                    duration=5,
                )
                return
            self.first_start = False
            self.dlg = MarraquetaDialog()
            self.lyr_data = []
            for dlg_row in self.dlg.rows:
                layer = dlg_row["layer"]
                _, info = read_raster(layer.publicSource(), data=False, info=True)
                self.lyr_data += [{"layer": layer, "info": info}]
                rimin, rimax = int(np.floor(info["Minimum"])), int(np.ceil(info["Maximum"]))
                qprint(f"{rimin=} {rimax=}")
                for name in ["a_spinbox", "b_spinbox", "a_slider", "b_slider"]:
                    ret_val = dlg_row[name].setRange(rimin, rimax)
                    qprint(f"{name=} {ret_val=}")
            qprint(f"{self.lyr_data=}")
            self.H = self.lyr_data[0]["info"]["RasterYSize"]
            self.W = self.lyr_data[0]["info"]["RasterXSize"]
            self.GT = self.lyr_data[0]["info"]["Transform"]
            self.crs_auth_id = self.lyr_data[0]["layer"].crs().authid()
            self.srs = osr.SpatialReference().ImportFromWkt(self.lyr_data[0]["layer"].crs().toWkt())
            qprint(f"H:{self.H} W:{self.W} GeoTransform:{self.GT} crs-auth-id:{self.crs_auth_id}, srs:{self.srs}")
            qprint("not checking if rasters match!", level=Qgis.Warning)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        qprint(f"{result=} {self.dlg.DialogCode()=}")
        # See if OK was pressed
        if result:
            self.dlg.rescale_weights()

            extent = self.iface.mapCanvas().extent()
            qprint(f"{extent=}")
            resolution = resolution_filter(extent, (1920, 1080), 100)
            qprint(f"{resolution=}")

            final_data = np.zeros(resolution[::-1], dtype=np.float32)
            did_any = False
            for dlg_row in self.dlg.rows:
                if dlg_row["weight_checkbox"].isChecked() and dlg_row["weight_spinbox"].value() != 0:
                    weight = dlg_row["weight_spinbox"].value()
                    lyr = self.lyr_data[dlg_row["i"]]
                    lyr_nodata = lyr["info"]["NoDataValue"]
                    griora = dlg_row["resample_dropdown"].currentIndex()
                    lyr_data, srs = get_sampled_raster_data(lyr["layer"].publicSource(), extent, resolution, griora)
                    # utility function dropdown current index
                    ufdci = dlg_row["ufunc_dropdown"].currentIndex()
                    if 0 == ufdci:  # min_max_scaling
                        new_data = min_max_scaling(lyr_data, lyr_nodata, invert=dlg_row["minmax_invert"].isChecked())
                        did_any = True
                    elif 1 == ufdci:  # bi_piecewise_linear
                        a = dlg_row["a_spinbox"].value()
                        b = dlg_row["b_spinbox"].value()
                        if a != b:
                            new_data = bi_piecewise_linear(
                                lyr_data, lyr_nodata, dlg_row["a_spinbox"].value(), dlg_row["b_spinbox"].value()
                            )
                            did_any = True
                        else:
                            qprint("a == b, skipping", level=Qgis.Warning)
                            continue
                    else:
                        qprint("Unknown utility function", level=Qgis.Critical)
                        return

                    qprint(f"{lyr['layer'].name()=} {np.histogram(new_data)=}")
                    final_data[lyr_data != lyr_nodata] += weight / 100 * new_data[lyr_data != lyr_nodata]

            if not did_any:
                qprint("Nothing to do, all layers unselected or 0 weight")
                return

            afile = create_sampled_raster(final_data, extent, srs, resolution)
            # add the raster layer to the canvas
            self.iface.addRasterLayer(afile, "final_data")


def min_max_scaling(data, nodata, invert=False):
    min_val = data[data != nodata].min()
    max_val = data[data != nodata].max()
    if max_val != min_val:
        ret_val = (data - min_val) / (max_val - min_val)
        if invert:
            return np.float32(1 - ret_val)
        return np.float32(ret_val)
    else:
        return np.zeros_like(data, dtype=np.float32)


def bi_piecewise_linear(data, nodata, a, b):
    ret_val = np.empty_like(data, dtype=np.float32)
    # linear scaling
    ret_val[data != nodata] = (data[data != nodata] - a) / (b - a)
    # clip to [0, 1]
    ret_val[ret_val < 0] = 0
    ret_val[ret_val > 1] = 1
    # keep nodata values
    ret_val[data == nodata] = data[data == nodata]
    return np.float32(ret_val)


def get_sampled_raster_data(raster_path, extent, resolution=(1920, 1080), griora=0):
    """Returns the data of the raster in the form of a numpy array, taken from the extent of the map canvas and resampled to resolution
    Args:
        raster_path (str): path to the raster file
        extent (QgsRectangle): extent of the map canvas
        resolution (tuple): resolution of the output array
    Return:
        data (np.array): numpy array with the data of the raster
        extent (QgsRectangle): extent of the map canvas
        srs (osr.SpatialReference): spatial reference of the raster
    Raises:
        ValueError: if the raster file could not be opened by gdal.Open

    Debug:
        from osgeo import gdal
        raster_path = iface.activeLayer().publicSource()
        extent = iface.mapCanvas().extent()
        resolution = (20, 80)
        resolution = (1920, 1080)
    """
    dataset = gdal.Open(raster_path)
    if dataset is None:
        raise ValueError("Could not open raster file")
    srs = osr.SpatialReference()
    if 0 != srs.ImportFromWkt(dataset.GetProjection()):
        qprint(f"SpatialReference ImportFromWkt failed {raster_path=} (maybe raster without CRS?)", level=Qgis.Critical)
    geotransform = dataset.GetGeoTransform()
    # print(f"{srs=}, {geotransform=}")
    band = dataset.GetRasterBand(1)
    # TODO: can we use the overview to speed up the process?
    # num_overviews = band.GetOverviewCount()
    # TODO: test raster rotado
    xoff = int((extent.xMinimum() - geotransform[0]) / geotransform[1])
    yoff = int((extent.yMaximum() - geotransform[3]) / geotransform[5])
    xsize = int((extent.xMaximum() - extent.xMinimum()) / geotransform[1])
    ysize = int((extent.yMinimum() - extent.yMaximum()) / geotransform[5])
    # print(f"{xoff=} {yoff=} {xsize=} {ysize=}")
    data = band.ReadAsArray(
        xoff=xoff,
        yoff=yoff,
        win_xsize=xsize,
        win_ysize=ysize,
        buf_xsize=resolution[0],
        buf_ysize=resolution[1],
        resample_alg=griora,
    )
    """
    ret_array = band1.ReadAsArray(
        xoff=xoff, yoff=yoff, win_xsize=xsize, win_ysize=ysize, buf_xsize=buf_xsize, buf_ysize=buf_ysize, buf_type=gdal.GDT_Float32
    )
    buf_type = 256 levels (0-255) is gdal.GDT_Byte
    resample_alg = 0 nearest neighbour, ...
    band1.ReadAsArray(xoff=0, yoff=0, xsize=None, ysize=None, buf_obj=None, buf_xsize=None, buf_ysize=None, buf_type=None, resample_alg=0, callback=None, callback_data=None, interleave='band', band_list=None)
    print(ret_array.shape, ret_array.dtype)
    tmp_data  = ret_array
    final_data = tmp_data
    """
    return data, srs


def create_sampled_raster(data, extent, srs, resolution, *args, **kwargs):
    """Create a new layer form numpy array data
    TODO: carry datatype
    TODO: carry nodata value
    """
    # data = data.astype(np.byte)
    # FIXME always float32
    data = data.astype(np.float32)
    afile = tempfile.mktemp(suffix=".tif")
    # dataset = gdal.GetDriverByName("GTiff").Create(afile, data.shape[1], data.shape[0], 1, gdal.GDT_Float32)
    dataset = gdal.GetDriverByName("GTiff").Create(afile, data.shape[1], data.shape[0], 1, gdal.GDT_Byte)

    new_geotransform = (
        extent.xMinimum(),
        (extent.xMaximum() - extent.xMinimum()) / resolution[0],
        0,  # TODO: ALLOW ROTATION
        extent.yMaximum(),
        0,  # TODO: ALLOW ROTATION
        (extent.yMinimum() - extent.yMaximum()) / resolution[1],
    )
    dataset.SetGeoTransform(new_geotransform)  # specify coords
    dataset.SetProjection(srs.ExportToWkt())  # export coords to file

    band = dataset.GetRasterBand(1)
    if 0 != band.SetNoDataValue(-9999):
        qprint("Set No Data failed", level=Qgis.Critical)
    if 0 != band.WriteArray(data):
        qprint("WriteArray failed", level=Qgis.Critical)

    # paint(band)

    dataset.FlushCache()  # write to disk
    dataset = None
    # iface.addRasterLayer(afile, "final_data")
    return afile


def paint(band: gdal.Band, colormap: str = "turbo") -> None:
    """Paints a gdal raster using band.SetRasterColorTable, only works for Byte and UInt16 bands
    Args:
        band (gdal.Band): band to paint
        colormap (str): name of the colormap to use
    """
    if band.DataType == gdal.GDT_Byte:
        # byte 2**8 = 256
        num_colors = 256
    elif band.DataType == gdal.GDT_UInt16:
        # uint16 2**16 = 65,536
        num_colors = 65536
    else:
        return

    from matplotlib import colormaps
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    from numpy import linspace

    cm = colormaps.get(colormap)
    if isinstance(cm, LinearSegmentedColormap):
        colors = cm(linspace(0, 1, num_colors))
    elif isinstance(cm, ListedColormap):
        colors = cm.resampled(num_colors).colors
    colors = (colors * 255).astype(int)

    color_table = gdal.ColorTable()
    for i, color in enumerate(colors):
        color_table.SetColorEntry(i, color)
    band.SetRasterColorTable(color_table)


def get_extent_size(extent: QgsRectangle):
    """Returns the width and height of the current displayed extent in meters"""
    # Create a CRS for meters (for example, WGS 84 / Pseudo-Mercator)
    crs_meters = QgsCoordinateReferenceSystem("EPSG:3857")

    # Get the current CRS
    crs_current = QgsProject.instance().crs()

    # Create a coordinate transform
    transform = QgsCoordinateTransform(crs_current, crs_meters, QgsProject.instance())

    # Transform the extent
    extent_meters = transform.transformBoundingBox(extent)

    # Get the width and height
    width = extent_meters.width()
    height = extent_meters.height()
    qprint(f"get_extent_size  {width=}, {height=}")
    return width, height


def resolution_filter(extent: QgsRectangle, resolution=(1920, 1080), pixel_size=100):
    """Returns a resolution that is at most the input resolution, else returns a smaller one."""
    extent_with, extent_height = get_extent_size(extent)
    extent_xpx = int(extent_with / pixel_size)
    extent_ypx = int(extent_height / pixel_size)
    resx = resolution[0] if extent_xpx > resolution[0] else extent_xpx
    resy = resolution[1] if extent_ypx > resolution[1] else extent_ypx
    qprint(f"resolution_filter {resx=}, {resy=}")
    return resx, resy


def current_displayed_pixels(iface):
    extent = iface.mapCanvas().extent()
    layer = iface.activeLayer()
    px_size_x = layer.rasterUnitsPerPixelX()
    px_size_y = layer.rasterUnitsPerPixelY()
    xsize = int((extent.xMaximum() - extent.xMinimum()) / px_size_x)
    ysize = int((extent.yMinimum() - extent.yMaximum()) / px_size_y)
    return xsize, ysize


def qprint(*args, tag="Marraqueta", level=Qgis.Info, sep=" ", end="", **kwargs):
    QgsMessageLog.logMessage(sep.join(map(str, args)) + end, tag, level, **kwargs)
