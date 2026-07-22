const STORAGE_KEYS = {
  team: "parallax.registration.team",
  members: "parallax.registration.members",
  proofs: "parallax.registration.proofs",
  reviews: "parallax.registration.reviews"
};

const MAX_UPLOAD_SIZE = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".pdf"];
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const TEAM_CODE_PATTERN = /^TEAM\d{4}$/;
const COLLEGE_OTHER_VALUE = "OTHER";

document.addEventListener("DOMContentLoaded", () => {
  setCurrentYear();
  highlightActiveNavigation();
  enableRevealAnimations();
  enableButtonRipples();
  attachTeamCodeFormatting();
  initializeCollegeFieldToggles();
  initializePasswordToggles();
  initializeSecretToggles();
  initializeLeaderForm();
  initializeLeaderEditForm();
  initializeMemberForm();
  initializeProofUploadForm();
  initializeReviewForm();
  initializeStoredSummaries();
});

function setCurrentYear() {
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = String(new Date().getFullYear());
  });
}

function highlightActiveNavigation() {
  const page = document.body.dataset.page;
  const navKey = page === "proof" ? "payment" : page;
  const activeLink = document.querySelector(`[data-nav="${navKey}"]`);

  if (activeLink) {
    activeLink.classList.add("is-active");
  }
}

function enableRevealAnimations() {
  const revealNodes = document.querySelectorAll("[data-reveal]");

  if (!revealNodes.length) {
    return;
  }

  if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    revealNodes.forEach((node) => {
      node.classList.remove("reveal-pending");
      node.classList.add("revealed");
    });
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }

      entry.target.classList.add("revealed");
      observer.unobserve(entry.target);
    });
  }, {
    threshold: 0.12
  });

  revealNodes.forEach((node) => {
    const rect = node.getBoundingClientRect();

    if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) {
      node.classList.remove("reveal-pending");
      node.classList.add("revealed");
      return;
    }

    node.classList.add("reveal-pending");
    observer.observe(node);
  });
}

function enableButtonRipples() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  document.querySelectorAll(".button, .parallax-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      const rect = button.getBoundingClientRect();
      const ripple = document.createElement("span");

      ripple.className = "ripple";
      ripple.style.left = `${event.clientX - rect.left}px`;
      ripple.style.top = `${event.clientY - rect.top}px`;

      button.appendChild(ripple);

      window.setTimeout(() => {
        ripple.remove();
      }, 720);
    });
  });
}

function attachTeamCodeFormatting() {
  document.querySelectorAll('input[name="team_code"]').forEach((input) => {
    input.addEventListener("input", () => {
      input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
    });
  });
}

function initializeCollegeFieldToggles() {
  document.querySelectorAll("[data-college-control]").forEach((select) => {
    syncCollegeFields(select);
    select.addEventListener("change", () => {
      syncCollegeFields(select);
      validateField(select);
    });
  });
}

function initializePasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const target = document.getElementById(button.dataset.target);

    if (!target) {
      return;
    }

    button.addEventListener("click", () => {
      const shouldReveal = target.type === "password";

      target.type = shouldReveal ? "text" : "password";
      button.textContent = shouldReveal ? "Hide" : "Show";
      button.setAttribute("aria-label", shouldReveal ? "Hide password" : "Show password");
    });
  });
}

function initializeSecretToggles() {
  document.querySelectorAll("[data-secret-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.target);

      if (!target) {
        return;
      }

      const shouldReveal = target.dataset.revealed !== "true";
      updateSecretFieldDisplay(target, button, shouldReveal);
    });

    const target = document.getElementById(button.dataset.target);

    if (target) {
      updateSecretFieldDisplay(target, button, false);
    }
  });
}

function initializeStoredSummaries() {
  const team = readStorage(STORAGE_KEYS.team);
  const latestProof = getLatestRecord(STORAGE_KEYS.proofs);

  setText("[data-team-code-display]", team?.code || "No team code yet");
  setText("[data-team-code-preview]", team?.code || "No team registered yet");
  setText("[data-team-name-display]", team?.teamName || "Waiting for leader registration");
  setText("[data-leader-name-display]", team?.leaderName || "Waiting for leader registration");
  setText("[data-team-status-display]", team?.status || "Pending registration");

  if (document.getElementById("leaderSuccess") && hasSavedTeam(team)) {
    renderLeaderSuccess(team, false);
  }

  if (document.getElementById("proofSuccess") && latestProof) {
    renderProofSuccess(latestProof, false);
  }
}

function initializeLeaderForm() {
  const form = document.getElementById("leaderRegistrationForm");

  if (!form) {
    return;
  }

  const alertBox = document.getElementById("leaderFormAlert");
  setupLiveValidation(form, alertBox);
  preventLeaderPasteActions(form, alertBox);

  if (hasSavedTeam(readStorage(STORAGE_KEYS.team))) {
    setLeaderFormVisibility(false);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please fix the highlighted fields before registering the team.");
      return;
    }

    const proofFile = form.querySelector('input[name="payment_proof"]').files[0];
    const teamPayload = createLeaderPayload(form, proofFile);

    writeStorage(STORAGE_KEYS.team, teamPayload);
    writeStorage(STORAGE_KEYS.members, []);
    writeStorage(STORAGE_KEYS.proofs, []);

    setFormAlert(alertBox, "", "");
    renderLeaderSuccess(teamPayload, true);
    initializeStoredSummaries();
    form.reset();
    clearFormErrors(form);

    const collegeSelect = form.querySelector("[data-college-control]");

    if (collegeSelect) {
      syncCollegeFields(collegeSelect);
    }
  });
}

function initializeLeaderEditForm() {
  const form = document.getElementById("leaderEditForm");

  if (!form) {
    return;
  }

  const alertBox = document.getElementById("leaderEditAlert");
  const openButton = document.getElementById("editLeaderDetailsButton");
  const closeButton = document.getElementById("cancelLeaderEditButton");

  setupLiveValidation(form, alertBox);

  if (openButton) {
    openButton.addEventListener("click", () => {
      const storedTeam = readStorage(STORAGE_KEYS.team);

      if (!hasSavedTeam(storedTeam)) {
        return;
      }

      populateLeaderEditForm(storedTeam);
      form.classList.remove("is-hidden");
      setFormAlert(alertBox, "", "");
      form.scrollIntoView({ behavior: getScrollBehavior(), block: "start" });
    });
  }

  if (closeButton) {
    closeButton.addEventListener("click", () => {
      form.classList.add("is-hidden");
      setFormAlert(alertBox, "", "");
      clearFormErrors(form);
      populateLeaderEditForm(readStorage(STORAGE_KEYS.team));
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please fix the highlighted fields before saving the changes.");
      return;
    }

    const storedTeam = readStorage(STORAGE_KEYS.team);

    if (!hasSavedTeam(storedTeam)) {
      setFormAlert(alertBox, "error", "No saved leader registration is available to update.");
      return;
    }

    const formData = new FormData(form);
    const nextPassword = String(formData.get("edit_password") || "").trim();
    const updatedTeam = {
      ...storedTeam,
      email: String(formData.get("edit_email") || "").trim(),
      phone: normalizePhone(String(formData.get("edit_phone") || "")),
      updatedAt: new Date().toISOString()
    };

    if (nextPassword) {
      updatedTeam.password = nextPassword;
      delete updatedTeam.passwordPlaceholder;
    }

    writeStorage(STORAGE_KEYS.team, updatedTeam);
    renderLeaderSuccess(updatedTeam, false);
    initializeStoredSummaries();
    populateLeaderEditForm(updatedTeam);
    clearFormErrors(form);
    setFormAlert(alertBox, "success", "Team contact details updated successfully.");
  });
}

function initializeMemberForm() {
  const form = document.getElementById("memberRegistrationForm");

  if (!form) {
    return;
  }

  const alertBox = document.getElementById("memberFormAlert");
  const teamCodeField = form.querySelector('input[name="team_code"]');
  const successPanel = document.getElementById("memberSuccess");

  setupLiveValidation(form, alertBox);

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please fix the highlighted fields before joining the team.");
      return;
    }

    const storedTeam = readStorage(STORAGE_KEYS.team);
    const submittedCode = teamCodeField.value.trim().toUpperCase();

    if (!hasSavedTeam(storedTeam) || storedTeam.code !== submittedCode) {
      setFieldError(teamCodeField, "This team code does not match the saved leader registration.");
      setFormAlert(alertBox, "error", "Invalid Team Code. Enter the exact code shared by the team leader.");

      if (successPanel) {
        successPanel.classList.add("is-hidden");
      }

      return;
    }

    const proofFile = form.querySelector('input[name="payment_proof"]').files[0];
    const existingMembers = readStorage(STORAGE_KEYS.members) || [];

    existingMembers.push(createMemberPayload(form, proofFile, submittedCode));

    writeStorage(STORAGE_KEYS.members, existingMembers);

    renderMemberSuccess(storedTeam, true);
    setFormAlert(alertBox, "success", "Joined Successfully. Your details have been linked to the saved team.");
    form.reset();
    clearFormErrors(form);

    const collegeSelect = form.querySelector("[data-college-control]");

    if (collegeSelect) {
      syncCollegeFields(collegeSelect);
    }
  });
}

function initializeProofUploadForm() {
  const form = document.getElementById("proofUploadForm");

  if (!form) {
    return;
  }

  const fileInput = form.querySelector('input[name="proof_file"]');
  const fileTrigger = form.querySelector("[data-file-trigger]");
  const dropzone = form.querySelector("[data-dropzone]");
  const fileMeta = form.querySelector("[data-file-meta]");
  const alertBox = document.getElementById("proofFormAlert");

  if (fileTrigger) {
    fileTrigger.addEventListener("click", () => {
      fileInput.click();
    });
  }

  fileInput.addEventListener("change", () => {
    updateDropzoneMeta(fileInput, fileMeta);
    validateField(fileInput);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const { files } = event.dataTransfer;

    if (!files || !files.length) {
      return;
    }

    const assigned = assignFiles(fileInput, files);

    if (!assigned) {
      setFormAlert(alertBox, "error", "Drag and drop is not supported here. Please use the Select File button.");
      return;
    }

    updateDropzoneMeta(fileInput, fileMeta);
    validateField(fileInput);
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please choose a valid file before uploading.");
      return;
    }

    const selectedFile = fileInput.files[0];
    const proofRecord = {
      ...buildFileSummary(selectedFile),
      teamCode: readStorage(STORAGE_KEYS.team)?.code || "Unlinked",
      uploadedAt: new Date().toISOString()
    };

    const proofEntries = readStorage(STORAGE_KEYS.proofs) || [];
    proofEntries.push(proofRecord);
    writeStorage(STORAGE_KEYS.proofs, proofEntries);

    renderProofSuccess(proofRecord, true);
    setFormAlert(alertBox, "success", "Payment Proof Uploaded Successfully. Waiting for Organizer Approval.");
    form.reset();
    updateDropzoneMeta(fileInput, fileMeta);
    clearFormErrors(form);
  });
}

function initializeReviewForm() {
  const form = document.getElementById("reviewForm");

  if (!form) {
    return;
  }

  const alertBox = document.getElementById("reviewFormAlert");
  const ratingInput = form.querySelector('input[name="overall_rating"]');
  const starButtons = form.querySelectorAll("[data-rating-value]");
  const successPanel = document.getElementById("reviewSuccess");

  setupLiveValidation(form, alertBox);

  starButtons.forEach((button) => {
    button.addEventListener("click", () => {
      ratingInput.value = button.dataset.ratingValue;
      updateStarRating(starButtons, Number(button.dataset.ratingValue));
      validateField(ratingInput);
    });
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please complete the rating and required text fields before submitting feedback.");
      return;
    }

    const formData = new FormData(form);
    const reviews = readStorage(STORAGE_KEYS.reviews) || [];

    reviews.push({
      teamCode: readStorage(STORAGE_KEYS.team)?.code || null,
      overallRating: Number(formData.get("overall_rating")),
      reviewTitle: String(formData.get("review_title") || "").trim(),
      comment: String(formData.get("comment") || "").trim(),
      suggestions: String(formData.get("suggestions") || "").trim(),
      submittedAt: new Date().toISOString()
    });

    writeStorage(STORAGE_KEYS.reviews, reviews);

    if (successPanel) {
      successPanel.classList.remove("is-hidden");
      successPanel.scrollIntoView({ behavior: getScrollBehavior(), block: "start" });
    }

    setFormAlert(alertBox, "success", "Thank you for your feedback.");
    form.reset();
    updateStarRating(starButtons, 0);
    clearFormErrors(form);
  });
}

function setupLiveValidation(form, alertBox) {
  const fields = getAllFormFields(form);

  fields.forEach((field) => {
    const eventName = field.type === "checkbox" || field.type === "file" || field.tagName === "SELECT" ? "change" : "blur";

    field.addEventListener(eventName, () => {
      validateField(field);
    });

    if (!["checkbox", "file", "hidden"].includes(field.type)) {
      field.addEventListener("input", () => {
        if (field.classList.contains("is-invalid")) {
          validateField(field);
        }
      });
    }
  });

  if (alertBox) {
    form.addEventListener("input", () => {
      if (alertBox.dataset.state === "error") {
        setFormAlert(alertBox, "", "");
      }
    });
  }
}

function validateForm(form) {
  return getFormFields(form).every((field) => validateField(field));
}

function validateField(field) {
  if (!field) {
    return true;
  }

  if (field.disabled) {
    clearFieldError(field);
    return true;
  }

  const label = getFieldLabel(field);

  if (field.type === "checkbox") {
    if (field.required && !field.checked) {
      setFieldError(field, `Please accept ${label.toLowerCase()}.`);
      return false;
    }

    clearFieldError(field);
    return true;
  }

  if (field.type === "file") {
    const file = field.files && field.files[0];

    if (field.required && !file) {
      setFieldError(field, `Please upload ${label.toLowerCase()}.`);
      return false;
    }

    if (file) {
      const fileError = validateFile(file);

      if (fileError) {
        setFieldError(field, fileError);
        return false;
      }
    }

    clearFieldError(field);
    return true;
  }

  const value = field.value.trim();
  const canonicalName = getCanonicalFieldName(field.name);

  if (field.required && !value) {
    setFieldError(field, `${label} is required.`);
    return false;
  }

  if (canonicalName === "confirm_password") {
    const passwordFieldName = field.name.startsWith("edit_") ? "edit_password" : "password";
    const passwordField = field.form ? field.form.querySelector(`[name="${passwordFieldName}"]`) : null;
    const passwordValue = passwordField ? passwordField.value.trim() : "";

    if ((passwordValue || value || field.required) && !value) {
      setFieldError(field, "Please confirm the password.");
      return false;
    }

    if (value && value !== passwordValue) {
      setFieldError(field, "Passwords do not match.");
      return false;
    }
  }

  if (canonicalName === "email" && value && !EMAIL_PATTERN.test(value)) {
    setFieldError(field, "Enter a valid email address.");
    return false;
  }

  if (canonicalName === "phone" && value) {
    const phoneDigits = normalizePhone(value);

    if (phoneDigits.length !== 10) {
      setFieldError(field, "Enter a valid 10-digit phone number.");
      return false;
    }
  }

  if (field.name === "team_code" && value && !TEAM_CODE_PATTERN.test(value.toUpperCase())) {
    setFieldError(field, "Enter a valid team code in the format TEAM4831.");
    return false;
  }

  if (field.type === "number" && value) {
    const numericValue = Number(value);
    const min = field.min ? Number(field.min) : null;
    const max = field.max ? Number(field.max) : null;

    if (min !== null && numericValue < min) {
      setFieldError(field, `${label} must be at least ${min}.`);
      return false;
    }

    if (max !== null && numericValue > max) {
      setFieldError(field, `${label} must be ${max} or below.`);
      return false;
    }
  }

  clearFieldError(field);
  return true;
}

function validateFile(file) {
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;

  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return "Upload a JPG, JPEG, PNG, or PDF file only.";
  }

  if (file.size > MAX_UPLOAD_SIZE) {
    return "File size must be 5 MB or smaller.";
  }

  return "";
}

function renderLeaderSuccess(team, shouldScroll) {
  const panel = document.getElementById("leaderSuccess");

  if (!panel) {
    return;
  }

  const passwordValue = team.password || team.passwordPlaceholder || "";

  setLeaderFormVisibility(false);
  setLeaderSummaryValue("teamName", team.teamName || "Not provided");
  setLeaderSummaryValue("leaderName", team.leaderName || "Not provided");
  setLeaderSummaryValue("collegeName", team.collegeName || "Not provided");
  setLeaderSummaryValue("registrationNumber", team.registrationNumber || "Not required");
  setLeaderSummaryValue("department", team.department || "Not provided");
  setLeaderSummaryValue("year", team.year || "Not provided");
  setLeaderSummaryValue("email", team.email || "Not provided");
  setLeaderSummaryValue("phone", team.phone || "Not provided");
  setLeaderSummaryValue("memberCount", team.memberCount ? String(team.memberCount) : "Not provided");
  setLeaderSummaryValue("status", team.status || "Pending Approval");
  setLeaderSummaryValue("createdAt", formatTimestamp(team.updatedAt || team.createdAt));
  toggleLeaderSummaryRow("registrationNumber", Boolean(team.registrationNumber));

  const teamCodeNode = document.getElementById("leaderTeamCode");
  const passwordNode = document.getElementById("leaderPasswordSummary");
  const passwordButton = document.querySelector('[data-secret-toggle][data-target="leaderPasswordSummary"]');

  if (teamCodeNode) {
    teamCodeNode.textContent = team.code || "TEAM0000";
  }

  if (passwordNode && passwordButton) {
    passwordNode.dataset.secretValue = passwordValue;
    updateSecretFieldDisplay(passwordNode, passwordButton, false);
  }

  populateLeaderEditForm(team);
  panel.classList.remove("is-hidden");

  if (shouldScroll) {
    panel.scrollIntoView({ behavior: getScrollBehavior(), block: "start" });
  }
}

function renderMemberSuccess(team, shouldScroll) {
  const panel = document.getElementById("memberSuccess");

  if (!panel) {
    return;
  }

  document.getElementById("memberTeamName").textContent = team.teamName;
  document.getElementById("memberLeaderName").textContent = team.leaderName;
  document.getElementById("memberStatus").textContent = team.status || "Pending Approval";
  panel.classList.remove("is-hidden");

  if (shouldScroll) {
    panel.scrollIntoView({ behavior: getScrollBehavior(), block: "start" });
  }
}

function renderProofSuccess(proofRecord, shouldScroll) {
  const panel = document.getElementById("proofSuccess");

  if (!panel) {
    return;
  }

  document.getElementById("proofFileName").textContent = proofRecord.name;
  document.getElementById("proofFileSize").textContent = proofRecord.sizeLabel;
  panel.classList.remove("is-hidden");

  if (shouldScroll) {
    panel.scrollIntoView({ behavior: getScrollBehavior(), block: "start" });
  }
}

function updateStarRating(starButtons, rating) {
  starButtons.forEach((button) => {
    const value = Number(button.dataset.ratingValue);
    button.classList.toggle("is-active", value <= rating);
  });
}

function updateDropzoneMeta(fileInput, fileMeta) {
  const selectedFile = fileInput.files && fileInput.files[0];

  if (!fileMeta) {
    return;
  }

  fileMeta.textContent = selectedFile
    ? `${selectedFile.name} (${formatFileSize(selectedFile.size)})`
    : "No file chosen yet";
}

function getFormFields(form) {
  return getAllFormFields(form).filter((field) => {
    return !field.disabled && !["submit", "reset", "button"].includes(field.type);
  });
}

function getAllFormFields(form) {
  return Array.from(form.querySelectorAll("input, select, textarea")).filter((field) => {
    return !["submit", "reset", "button"].includes(field.type);
  });
}

function setFieldError(field, message) {
  if (!field) {
    return;
  }

  const wrapper = field.closest(".field");
  const errorNode = wrapper ? wrapper.querySelector(".field-error") : null;

  field.classList.add("is-invalid");
  field.setAttribute("aria-invalid", "true");

  if (errorNode) {
    errorNode.textContent = message;
  }
}

function clearFieldError(field) {
  if (!field) {
    return;
  }

  const wrapper = field.closest(".field");
  const errorNode = wrapper ? wrapper.querySelector(".field-error") : null;

  field.classList.remove("is-invalid");
  field.removeAttribute("aria-invalid");

  if (errorNode) {
    errorNode.textContent = "";
  }
}

function clearFormErrors(form) {
  Array.from(form.querySelectorAll("input, select, textarea")).forEach((field) => clearFieldError(field));
}

function setFormAlert(alertBox, state, message) {
  if (!alertBox) {
    return;
  }

  if (!state || !message) {
    alertBox.textContent = "";
    alertBox.dataset.state = "";
    alertBox.classList.remove("is-visible");
    return;
  }

  alertBox.textContent = message;
  alertBox.dataset.state = state;
  alertBox.classList.add("is-visible");
}

function getFieldLabel(field) {
  return field.dataset.label || field.closest(".field")?.querySelector("label")?.textContent?.trim() || "This field";
}

function getCanonicalFieldName(name) {
  return name.startsWith("edit_") ? name.slice(5) : name;
}

function syncCollegeFields(select) {
  const form = select.closest("form");

  if (!form) {
    return;
  }

  const selectedOption = select.selectedOptions[0];
  const isOtherCollege = select.value === COLLEGE_OTHER_VALUE;
  const isVitCollege = selectedOption?.dataset.isVit === "true";
  const otherCollegeWrapper = form.querySelector("[data-other-college-wrapper]");
  const otherCollegeInput = form.querySelector('input[name="other_college_name"]');
  const registrationWrapper = form.querySelector("[data-registration-wrapper]");
  const registrationInput = form.querySelector('input[name="registration_number"]');

  toggleConditionalField(otherCollegeWrapper, otherCollegeInput, isOtherCollege);
  toggleConditionalField(registrationWrapper, registrationInput, isVitCollege);
}

function toggleConditionalField(wrapper, field, shouldShow) {
  if (!wrapper || !field) {
    return;
  }

  wrapper.classList.toggle("is-hidden", !shouldShow);
  field.disabled = !shouldShow;
  field.required = shouldShow;

  if (!shouldShow) {
    field.value = "";
    clearFieldError(field);
  }
}

function createLeaderPayload(form, proofFile) {
  const formData = new FormData(form);

  return {
    code: generateTeamCode(),
    teamName: String(formData.get("team_name") || "").trim(),
    leaderName: String(formData.get("leader_name") || "").trim(),
    registrationNumber: readConditionalRegistrationNumber(formData),
    collegeName: resolveCollegeName(formData),
    department: String(formData.get("department") || "").trim(),
    year: String(formData.get("year") || ""),
    email: String(formData.get("email") || "").trim(),
    phone: normalizePhone(String(formData.get("phone") || "")),
    memberCount: Number(formData.get("member_count")),
    password: String(formData.get("password") || "").trim(),
    paymentProof: buildFileSummary(proofFile),
    status: "Pending Approval",
    createdAt: new Date().toISOString()
  };
}

function createMemberPayload(form, proofFile, submittedCode) {
  const formData = new FormData(form);

  return {
    teamCode: submittedCode,
    memberName: String(formData.get("member_name") || "").trim(),
    registrationNumber: readConditionalRegistrationNumber(formData),
    collegeName: resolveCollegeName(formData),
    department: String(formData.get("department") || "").trim(),
    year: String(formData.get("year") || ""),
    email: String(formData.get("email") || "").trim(),
    phone: normalizePhone(String(formData.get("phone") || "")),
    paymentProof: buildFileSummary(proofFile),
    joinedAt: new Date().toISOString(),
    status: "Pending Approval"
  };
}

function resolveCollegeName(formData) {
  const selectedCollege = String(formData.get("college_name") || "").trim();

  if (selectedCollege === COLLEGE_OTHER_VALUE) {
    return String(formData.get("other_college_name") || "").trim();
  }

  return selectedCollege;
}

function readConditionalRegistrationNumber(formData) {
  return String(formData.get("registration_number") || "").trim();
}

function populateLeaderEditForm(team) {
  const form = document.getElementById("leaderEditForm");

  if (!form || !team) {
    return;
  }

  const emailField = form.querySelector('[name="edit_email"]');
  const phoneField = form.querySelector('[name="edit_phone"]');
  const passwordField = form.querySelector('[name="edit_password"]');
  const confirmField = form.querySelector('[name="edit_confirm_password"]');

  if (emailField) {
    emailField.value = team.email || "";
  }

  if (phoneField) {
    phoneField.value = team.phone || "";
  }

  if (passwordField) {
    passwordField.value = "";
    passwordField.type = "password";
  }

  if (confirmField) {
    confirmField.value = "";
    confirmField.type = "password";
  }

  form.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const target = document.getElementById(button.dataset.target);

    if (target && form.contains(target)) {
      button.textContent = "Show";
      button.setAttribute("aria-label", "Show password");
    }
  });
}

function preventLeaderPasteActions(form, alertBox) {
  const blockedEvents = ["copy", "cut", "paste", "drop"];
  const fields = form.querySelectorAll('input:not([type="file"]):not([type="checkbox"]):not([type="submit"]):not([type="button"]), textarea');

  fields.forEach((field) => {
    blockedEvents.forEach((eventName) => {
      field.addEventListener(eventName, (event) => {
        if (field.disabled) {
          return;
        }

        event.preventDefault();
        setFormAlert(alertBox, "error", "Please type leader details manually. Copy, cut, paste, and drag-drop are disabled in this form.");
      });
    });
  });
}

function setLeaderFormVisibility(shouldShow) {
  const formShell = document.getElementById("leaderFormShell");

  if (!formShell) {
    return;
  }

  formShell.classList.toggle("is-hidden", !shouldShow);
}

function setLeaderSummaryValue(key, value) {
  document.querySelectorAll(`[data-leader-summary="${key}"]`).forEach((node) => {
    node.textContent = value;
  });
}

function toggleLeaderSummaryRow(key, shouldShow) {
  document.querySelectorAll(`[data-leader-summary-row="${key}"]`).forEach((node) => {
    node.classList.toggle("is-hidden", !shouldShow);
  });
}

function updateSecretFieldDisplay(target, button, shouldReveal) {
  const secretValue = target.dataset.secretValue || "";

  target.dataset.revealed = shouldReveal ? "true" : "false";
  target.textContent = shouldReveal ? secretValue : maskPassword(secretValue);

  if (button) {
    button.hidden = !secretValue;
    button.textContent = shouldReveal ? "Hide" : "View";
  }
}

function maskPassword(value) {
  return value ? "•".repeat(Math.max(value.length, 8)) : "Not set";
}

function formatTimestamp(value) {
  if (!value) {
    return "Not available";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(parsed);
}

function hasSavedTeam(team) {
  return Boolean(team?.code && team?.teamName);
}

function generateTeamCode() {
  let generatedCode = "";
  const existingTeam = readStorage(STORAGE_KEYS.team);

  do {
    generatedCode = `TEAM${Math.floor(1000 + Math.random() * 9000)}`;
  } while (existingTeam && existingTeam.code === generatedCode);

  return generatedCode;
}

function buildFileSummary(file) {
  if (!file) {
    return {
      name: "",
      size: 0,
      sizeLabel: "0 B",
      type: ""
    };
  }

  return {
    name: file.name,
    size: file.size,
    sizeLabel: formatFileSize(file.size),
    type: file.type || "application/octet-stream"
  };
}

function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function normalizePhone(value) {
  return value.replace(/\D/g, "");
}

function assignFiles(input, fileList) {
  if (typeof DataTransfer === "undefined") {
    return false;
  }

  try {
    const transfer = new DataTransfer();
    Array.from(fileList).forEach((file) => transfer.items.add(file));
    input.files = transfer.files;
    return true;
  } catch (error) {
    return false;
  }
}

function setText(selector, value) {
  document.querySelectorAll(selector).forEach((node) => {
    node.textContent = value;
  });
}

function getLatestRecord(storageKey) {
  const records = readStorage(storageKey) || [];
  return records.length ? records[records.length - 1] : null;
}

function readStorage(key) {
  try {
    const rawValue = window.localStorage.getItem(key);
    return rawValue ? JSON.parse(rawValue) : null;
  } catch (error) {
    return null;
  }
}

function writeStorage(key, value) {
  window.localStorage.setItem(key, JSON.stringify(value));
}

function getScrollBehavior() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}
