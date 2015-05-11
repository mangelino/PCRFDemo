var app = angular.module("MyApp", []);

app.controller("CustomersController", function($scope, $http) {
  $http.get("http://localhost:5000/").
    success(function(data) {
      $scope.names = data;
    });
});

