(function ($) {
  "use strict";

  function getRoleCode(selectElement) {
    // Get the role mappings from data attribute
    var roleMappings = JSON.parse($(selectElement).attr("data-role-mappings"));
    // Get the selected UUID
    var selectedId = $(selectElement).val();
    // Return the corresponding role code
    return roleMappings[selectedId];
  }

  window.handleRoleChange = function (selectElement) {
    var roleCode = getRoleCode(selectElement);
    console.log("Selected role code:", roleCode); // For debugging

    // Hide all inline groups first
    $(".inline-group").hide();

    // Show the relevant inline group based on role code
    var inlineMapping = {
      DOCTOR: ".doctorprofile",
      NURSE: ".nurseprofile",
      TECHNICIAN: ".technicianprofile",
    };

    var relevantInline = inlineMapping[roleCode];
    if (relevantInline) {
      $(relevantInline).closest(".inline-group").show();
    }
  };

  $(document).ready(function () {
    // Initial setup - hide all inline groups
    $(".inline-group").hide();

    // Show relevant inline if role is already selected
    var roleSelect = $("#id_role");
    if (roleSelect.val()) {
      handleRoleChange(roleSelect[0]);
    }

    // If this is an edit form, disable role field
    if (
      $("#id_role").closest("form").find('input[name="_changelist_filters"]')
        .length > 0
    ) {
      $("#id_role").prop("disabled", true);
    }
  });
})(django.jQuery);
