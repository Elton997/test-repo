import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { MainLayoutComponent } from './layout/main-layout/main-layout.component';
import { AuthLayoutComponent } from './layout/auth-layout/auth-layout.component';
import { AuthGuard } from './guards/auth.guard';
import { Menu, SubMenu } from './menu.enum';

export const routes: Routes = [
  {
    path: 'login',
    component: AuthLayoutComponent,
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./components/login/login.component').then(m => m.LoginComponent),
      },
    ],
  },
  {
    path: '',
    canActivate: [AuthGuard],
    component: MainLayoutComponent,
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Locations,
        loadComponent: () =>
          import('./components/location-list/location-list.component').then(m => m.LocationListComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Locations + '/add',
        loadComponent: () =>
          import('./components/add-location/add-location.component').then(m => m.AddLocationComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Locations + '/edit/:LocationID',
        loadComponent: () =>
          import('./components/add-location/add-location.component').then(m => m.AddLocationComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Buildings,
        loadComponent: () =>
          import('./components/buildings-list/buildings-list.component').then(m => m.BuildingsListComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Buildings + '/add',
        loadComponent: () =>
          import('./components/add-building/add-building.component').then(m => m.AddBuildingComponent),
      },
      {
        path: Menu.Organization + '/' + SubMenu.Buildings + '/edit/:BuildingID',
        loadComponent: () =>
          import('./components/add-building/add-building.component').then(m => m.AddBuildingComponent),
      },
      {
        path: Menu.Rack_Management + '/' + SubMenu.Racks,
        loadComponent: () =>
          import('./components/racks-list/racks-list.component').then(m => m.RacksListComponent),
      },
      {
        path: Menu.Rack_Management + '/' + SubMenu.Racks + '/add',
        loadComponent: () =>
          import('./components/add-racks/add-racks.component').then(m => m.AddRacksComponent),
      },
      {
        path: Menu.Rack_Management + '/' + SubMenu.Racks + '/edit/:rackID',
        loadComponent: () =>
          import('./components/add-racks/add-racks.component').then(m => m.AddRacksComponent),
      },
      {
        path: Menu.Rack_Management + '/' + SubMenu.Racks + '/:rackId',
        loadComponent: () =>
          import('./components/rack-details/rack-details.component').then(m => m.RackDetailsComponent),
        canActivate: [AuthGuard]
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Devices,
        loadComponent: () =>
          import('./components/device-list/device-list.component').then(m => m.DeviceListComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Devices + '/add',
        loadComponent: () =>
          import('./components/add-device/add-device.component').then(m => m.AddDeviceComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Devices + '/edit/:deviceID',
        loadComponent: () =>
          import('./components/add-device/add-device.component').then(m => m.AddDeviceComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Devices + '/:deviceID',
        loadComponent: () =>
          import('./components/device-details/device-details.component').then(m => m.DeviceDetailsComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.DeviceTypes,
        loadComponent: () =>
          import('./components/device-type-list/device-type-list.component').then(m => m.DeviceTypeListComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.DeviceTypes + '/add',
        loadComponent: () =>
          import('./components/add-device-type/add-device-type.component').then(m => m.AddDeviceTypeComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.DeviceTypes + '/edit/:devicetypeID',
        loadComponent: () =>
          import('./components/add-device-type/add-device-type.component').then(m => m.AddDeviceTypeComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.DeviceTypes + '/:device_type',
        loadComponent: () =>
          import('./components/device-type-details/device-type-details.component').then(m => m.DeviceTypeDetailsComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Manufacturers,
        loadComponent: () =>
          import('./components/manufacturers/manufacturers.component').then(m => m.ManufacturersComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Manufacturers + '/add',
        loadComponent: () =>
          import('./components/add-manufacturer/add-manufacturer.component').then(m => m.AddManufacturerComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Manufacturers + '/edit/:ManufacterID',
        loadComponent: () =>
          import('./components/add-manufacturer/add-manufacturer.component').then(m => m.AddManufacturerComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Manufacturers + '/:manufacturerName',
        loadComponent: () =>
          import('./components/manufacturers-details/manufacturers-details.component').then(m => m.ManufacturersDetailsComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Models,
        loadComponent: () =>
          import('./components/models/models.component').then(m => m.ModelsComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Models + '/add',
        loadComponent: () =>
          import('./components/add-model/add-model.component').then(m => m.AddModelComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Models + '/edit/:model_name',
        loadComponent: () =>
          import('./components/add-model/add-model.component').then(m => m.AddModelComponent),
      },
      {
        path: Menu.Device_Management + '/' + SubMenu.Models + '/:model_name',
        loadComponent: () =>
          import('./components/models-details/models-details.component').then(m => m.ModelsDetailsComponent),
      }
    ],
  },
  { path: '**', redirectTo: 'login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
