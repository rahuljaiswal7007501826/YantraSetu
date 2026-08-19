// Exactly the Hindi strings spoken aloud by <SpeakButton> (Phase 18) - faithful
// translations of the on-screen copy, nothing freshly invented. This is a tiny,
// scoped lookup (NOT a full i18n framework): only what is read aloud lives here.
// Interpolated values (machine type, CHC name) are the same values shown on the
// screen, so the audio matches what the farmer sees.

export const hiStrings = {
  // Shown after a request is submitted (RequestDetailsPage confirmation banner).
  // On screen: "Your request has been registered successfully."
  requestRegistered: 'आपका अनुरोध सफलतापूर्वक दर्ज हो गया है।',

  // My Booking - assigned machine, when the CHC has confirmed it
  // (status allocated/scheduled; on-screen subtitle "Confirmed by your CHC").
  assignmentConfirmed: ({ machineType, chcName }) =>
    `${chcName} द्वारा आपके अनुरोध के लिए ${machineType} मशीन की पुष्टि कर दी गई है।`,

  // My Booking - assigned machine, still a recommendation (status pending;
  // on-screen "Preview from the allocation engine" + the time-slot note).
  assignmentPreview: ({ machineType, chcName }) =>
    `नेटवर्क आपके अनुरोध के लिए ${chcName} की ${machineType} मशीन सुझा रहा है। सही समय आपका CHC तय करेगा।`,

  // My Booking - no machine yet. On screen: "No machine is available for your
  // request yet. The network is looking for one."
  noMachineYet:
    'अभी आपके अनुरोध के लिए कोई मशीन उपलब्ध नहीं है। नेटवर्क एक मशीन ढूंढ रहा है।',

  // File Complaint page instructions (spoken via SpeakButton). On screen:
  // "File your complaint here. Pick a category and write the details, or press
  // the mic button to speak."
  complaintInstructions:
    'अपनी शिकायत यहाँ दर्ज करें। श्रेणी चुनें और विवरण लिखें, या माइक बटन दबाकर बोलें।',
}
