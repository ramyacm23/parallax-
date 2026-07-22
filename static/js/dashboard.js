document.addEventListener("DOMContentLoaded", () => {
  initializeCollegeSelection();
});

function initializeCollegeSelection() {
  document.querySelectorAll("[data-college-control]").forEach((select) => {
    syncCollegeFields(select);
    select.addEventListener("change", () => syncCollegeFields(select));
  });
}

function syncCollegeFields(select) {
  const form = select.closest("form");

  if (!form) {
    return;
  }

  const selectedOption = select.selectedOptions[0];
  const registrationWrapper = form.querySelector("[data-registration-wrapper]");
  const registrationField = form.querySelector('[name="reg_number"]');
  const otherCollegeWrapper = form.querySelector("[data-other-college-wrapper]");
  const otherCollegeField = form.querySelector('[name="other_college_name"]');
  const shouldShowRegistration = selectedOption && selectedOption.dataset.isVit === "true";
  const shouldShowOtherCollege = select.value === "OTHER";

  toggleField(registrationWrapper, registrationField, shouldShowRegistration);
  toggleField(otherCollegeWrapper, otherCollegeField, shouldShowOtherCollege);
}

function toggleField(wrapper, field, shouldShow) {
  if (!wrapper || !field) {
    return;
  }

  wrapper.classList.toggle("hidden", !shouldShow);
  field.disabled = !shouldShow;
  field.required = shouldShow;

  if (!shouldShow) {
    field.value = "";
  }
}
