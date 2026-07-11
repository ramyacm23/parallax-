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

document.addEventListener("DOMContentLoaded", () => {
  setCurrentYear();
  highlightActiveNavigation();
  enableRevealAnimations();
  enableButtonRipples();
  attachTeamCodeFormatting();
  initializeStoredSummaries();
  initializeLeaderForm();
  initializeMemberForm();
  initializeProofUploadForm();
  initializeReviewForm();
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
    revealNodes.forEach((node) => node.classList.add("revealed"));
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
    threshold: 0.18
  });

  revealNodes.forEach((node) => observer.observe(node));
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

function initializeStoredSummaries() {
  const team = readStorage(STORAGE_KEYS.team);
  const latestProof = getLatestRecord(STORAGE_KEYS.proofs);

  setText("[data-team-code-display]", team?.code || "No team code yet");
  setText("[data-team-code-preview]", team?.code || "No team registered yet");
  setText("[data-team-name-display]", team?.teamName || "Waiting for leader registration");
  setText("[data-leader-name-display]", team?.leaderName || "Waiting for leader registration");
  setText("[data-team-status-display]", team?.status || "Pending registration");

  const leaderSuccess = document.getElementById("leaderSuccess");
  const proofSuccess = document.getElementById("proofSuccess");

  if (leaderSuccess && team) {
    renderLeaderSuccess(team, false);
  }

  if (proofSuccess && latestProof) {
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

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!validateForm(form)) {
      setFormAlert(alertBox, "error", "Please fix the highlighted fields before registering the team.");
      return;
    }

    const teamCode = generateTeamCode();
    const proofFile = form.querySelector('input[name="payment_proof"]').files[0];
    const formData = new FormData(form);
    const teamPayload = {
      code: teamCode,
      teamName: formData.get("team_name").trim(),
      leaderName: formData.get("leader_name").trim(),
      registrationNumber: formData.get("registration_number").trim(),
      collegeName: formData.get("college_name").trim(),
      department: formData.get("department").trim(),
      year: formData.get("year"),
      email: formData.get("email").trim(),
      phone: normalizePhone(formData.get("phone")),
      memberCount: Number(formData.get("member_count")),
      passwordPlaceholder: formData.get("password").trim(),
      paymentProof: buildFileSummary(proofFile),
      status: "Pending Approval",
      createdAt: new Date().toISOString()
    };

    writeStorage(STORAGE_KEYS.team, teamPayload);
    writeStorage(STORAGE_KEYS.members, []);
    writeStorage(STORAGE_KEYS.proofs, []);

    renderLeaderSuccess(teamPayload, true);
    initializeStoredSummaries();
    setFormAlert(alertBox, "success", "Registration Successful. Your team code has been generated and stored locally.");
    form.reset();
    clearFormErrors(form);
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

    if (!storedTeam || storedTeam.code !== submittedCode) {
      setFieldError(teamCodeField, "This team code does not match the saved leader registration.");
      setFormAlert(alertBox, "error", "Invalid Team Code. Enter the exact code shared by the team leader.");

      if (successPanel) {
        successPanel.classList.add("is-hidden");
      }

      return;
    }

    const proofFile = form.querySelector('input[name="payment_proof"]').files[0];
    const formData = new FormData(form);
    const existingMembers = readStorage(STORAGE_KEYS.members) || [];

    existingMembers.push({
      teamCode: submittedCode,
      memberName: formData.get("member_name").trim(),
      registrationNumber: formData.get("registration_number").trim(),
      collegeName: formData.get("college_name").trim(),
      department: formData.get("department").trim(),
      year: formData.get("year"),
      email: formData.get("email").trim(),
      phone: normalizePhone(formData.get("phone")),
      paymentProof: buildFileSummary(proofFile),
      joinedAt: new Date().toISOString(),
      status: "Pending Approval"
    });

    writeStorage(STORAGE_KEYS.members, existingMembers);

    renderMemberSuccess(storedTeam, true);
    setFormAlert(alertBox, "success", "Joined Successfully. Your details have been linked to the saved team.");
    form.reset();
    clearFormErrors(form);
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
      reviewTitle: formData.get("review_title").trim(),
      comment: formData.get("comment").trim(),
      suggestions: formData.get("suggestions").trim(),
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
  const fields = getFormFields(form);

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

  if (field.required && !value) {
    setFieldError(field, `${label} is required.`);
    return false;
  }

  if (field.name === "email" && value && !EMAIL_PATTERN.test(value)) {
    setFieldError(field, "Enter a valid email address.");
    return false;
  }

  if (field.name === "phone" && value) {
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

  document.getElementById("leaderTeamCode").textContent = team.code;
  document.getElementById("leaderTeamName").textContent = team.teamName;
  document.getElementById("leaderStatus").textContent = team.status;
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
  document.getElementById("memberStatus").textContent = team.status;
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
  return Array.from(form.querySelectorAll("input, select, textarea")).filter((field) => {
    return !["submit", "reset", "button"].includes(field.type);
  });
}

function setFieldError(field, message) {
  const wrapper = field.closest(".field");
  const errorNode = wrapper ? wrapper.querySelector(".field-error") : null;

  field.classList.add("is-invalid");
  field.setAttribute("aria-invalid", "true");

  if (errorNode) {
    errorNode.textContent = message;
  }
}

function clearFieldError(field) {
  const wrapper = field.closest(".field");
  const errorNode = wrapper ? wrapper.querySelector(".field-error") : null;

  field.classList.remove("is-invalid");
  field.removeAttribute("aria-invalid");

  if (errorNode) {
    errorNode.textContent = "";
  }
}

function clearFormErrors(form) {
  getFormFields(form).forEach((field) => clearFieldError(field));
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

function generateTeamCode() {
  let generatedCode = "";
  const existingTeam = readStorage(STORAGE_KEYS.team);

  do {
    generatedCode = `TEAM${Math.floor(1000 + Math.random() * 9000)}`;
  } while (existingTeam && existingTeam.code === generatedCode);

  return generatedCode;
}

function buildFileSummary(file) {
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
