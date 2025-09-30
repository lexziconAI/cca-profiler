"""
Load and validate JSON text bank for CCIP.

This module loads the predefined text bank and validates all required dimensions,
bands, and text entries exist.
"""

# KS_TEXTS: Key Strengths text for High and Very High bands
KS_TEXTS = {
    "DT": {
        "High": "You communicate with clarity and honesty, ensuring that expectations and feedback are well understood.\nYour ability to balance directness with cultural sensitivity helps you give clear guidance without creating defensiveness, a key factor in building psychological safety.\nBecause you consistently express both what needs to be done and why it matters, you minimise misunderstandings and keep projects on track.",
        "Very High": "You communicate with exceptional clarity and candid honesty, ensuring that expectations and feedback are unmistakably understood.\nYour strong ability to balance directness with thoughtful cultural sensitivity helps you give clear guidance without creating defensiveness, a crucial factor in building psychological safety.\nBecause you consistently and explicitly express both what needs to be done and why it matters, you reliably minimise misunderstandings and keep projects firmly on track."
    },
    "TR": {
        "High": "You manage the balance between getting things done and nurturing relationships with skill.\nThis allows you to meet deadlines without sacrificing team cohesion.\nYour ability to adapt, sometimes prioritising efficiency and at other times focusing on rapport, creates resilient, high-performing teams. Colleagues value you as someone who drives outcomes while ensuring people feel respected and included.",
        "Very High": "You manage the balance between getting things done and nurturing relationships with notable skill, which allows you to meet deadlines while maintaining strong team cohesion.\nYour highly adaptive ability to switch focus, sometimes prioritising efficiency and at other times rapport, creates resilient, consistently high-performing teams.\nColleagues strongly value you as someone who drives outcomes while ensuring people feel respected and included."
    },
    "CO": {
        "High": "You approach conflict as an opportunity to clarify issues and strengthen collaboration.\nThis creates space for innovation and better decisions.\nYour comfort in addressing disagreements early helps prevent small issues from escalating and keeps energy focused on solutions. By modelling constructive conflict management, you help build a culture where diverse opinions are valued and integrated.",
        "Very High": "You approach conflict as a valuable opportunity to clarify issues and strengthen collaboration, which consistently creates space for innovation and better decisions.\nYour strong comfort in addressing disagreements early helps prevent small issues from escalating and keeps energy tightly focused on solutions.\nBy reliably modelling constructive conflict management, you help build a culture where diverse opinions are genuinely valued and effectively integrated."
    },
    "CA": {
        "High": "You read cultural cues quickly and adjust your communication and behaviour with ease, enabling smooth collaboration across geographies and teams.\nThis flexibility helps you build rapport with clients and colleagues from diverse backgrounds, strengthening partnerships and reducing misunderstandings.\nYour openness to different customs and practices demonstrates respect and enhances organisational reputation.",
        "Very High": "You read cultural cues very quickly and adjust your communication and behaviour with notable ease, enabling smooth collaboration across geographies and teams.\nThis pronounced flexibility helps you build strong rapport with clients and colleagues from diverse backgrounds, strengthening partnerships and reducing misunderstandings.\nYour evident openness to different customs and practices demonstrates deep respect and enhances organisational reputation."
    },
    "EP": {
        "High": "You naturally seek to understand others' thoughts and emotions, enabling you to build trust and influence without authority.\nColleagues feel heard and valued in your presence, which strengthens engagement and loyalty.\nYour capacity to integrate multiple viewpoints leads to more inclusive decisions and stronger team cohesion.",
        "Very High": "You naturally and actively seek to understand others' thoughts and emotions, enabling you to build strong trust and influence without authority.\nColleagues consistently feel heard and genuinely valued in your presence, which strengthens engagement and loyalty.\nYour strong capacity to integrate multiple viewpoints leads to more inclusive decisions and robust team cohesion."
    }
}

# DA_TEXTS: Development Areas text for Developing and Low/Limited bands
DA_TEXTS = {
    "DT": {
        "Developing": "Your current style may at times leave some room for ambiguity, causing others to guess at priorities or next steps.\nYou might occasionally avoid difficult conversations or soften messages enough that key information is partly lost.\nDeveloping greater clarity, while respecting cultural nuances, will help you build trust and reduce rework or conflict.",
        "Low / Limited": "Your current style often leaves considerable room for ambiguity, causing others to guess at priorities or next steps.\nYou may frequently avoid difficult conversations or soften messages so much that key information is lost.\nEstablishing greater clarity, while still respecting cultural nuances, will help you rebuild trust and significantly reduce rework or conflict."
    },
    "TR": {
        "Developing": "Your current pattern may sometimes tilt too heavily toward either tasks or relationships, which can lead to occasional missed deadlines or disengaged team members.\nThere may be times when relational needs are overlooked in the drive for efficiency, or where progress slows because harmony is prioritised over results.\nLearning to flex more consciously between task and relationship focus will help you maintain productivity and strengthen trust simultaneously.",
        "Low / Limited": "Your current pattern often tilts heavily toward either tasks or relationships, which can lead to repeated missed deadlines or disengaged team members.\nRelational needs are frequently overlooked in the drive for efficiency, or progress often slows because harmony is prioritised over results.\nLearning to flex deliberately between task and relationship focus is essential to restore productivity and rebuild trust."
    },
    "CO": {
        "Developing": "You may hesitate to surface conflict or wait until issues become urgent, which can allow small problems to grow.\nWhen conflict does arise, you might sometimes withdraw or react defensively, reducing trust and slowing resolution.\nDeveloping skills to initiate timely, balanced conflict conversations will increase team resilience and creative problem solving.",
        "Low / Limited": "You often hesitate to surface conflict or wait until issues become urgent, which allows small problems to grow significantly.\nWhen conflict arises, you may withdraw or react defensively, which reduces trust and slows resolution.\nEstablishing skills to initiate timely, balanced conflict conversations is essential to strengthen team resilience and improve problem solving."
    },
    "CA": {
        "Developing": "You may sometimes default to familiar communication styles, missing subtle cues that a different approach is needed.\nThere can be a tendency to rely on assumptions about other cultures rather than pausing to learn or ask questions.\nBuilding greater awareness of cross-cultural norms and practising adaptive strategies will expand your effectiveness in global or multi-cultural settings.",
        "Low / Limited": "You often default to familiar communication styles, missing important cues that a different approach is needed.\nThere is a frequent tendency to rely on assumptions about other cultures rather than pausing to learn or ask questions.\nEstablishing greater awareness of cross-cultural norms and consistently practising adaptive strategies will be essential to operate effectively in global or multi-cultural settings."
    },
    "EP": {
        "Developing": "In high-pressure situations, you may at times focus more on tasks than on understanding the emotional context, which can erode trust.\nAt times you may listen without fully integrating what you have heard into next steps, missing chances to strengthen collaboration.\nDeliberately pausing to explore how others experience a situation, and how that should shape your response, will deepen relationships and improve outcomes.",
        "Low / Limited": "In high-pressure situations, you often focus on tasks rather than understanding the emotional context, which erodes trust.\nYou may listen without integrating what you have heard into next steps, which repeatedly misses chances to strengthen collaboration.\nEstablishing a deliberate pause to explore how others experience a situation, and allowing that to shape your response, is essential to repair relationships and improve outcomes."
    }
}

# PR_TEXTS: Practical Recommendations text (all dimensions)
PR_TEXTS = {
    "DT": 'Practise concise "what–why–next" framing in meetings to improve clarity and focus.\nSeek regular feedback on the clarity of both written and verbal messages to identify blind spots.\nRole-play challenging conversations with a mentor or coach to build skill and confidence under pressure.',
    "TR": "Schedule brief relationship-building check-ins during busy projects to strengthen trust without losing momentum.\nBalance meeting agendas to include both task updates and discussions about team well-being and collaboration.\nReflect weekly on recent interactions to ensure neither task completion nor relationship maintenance is being overlooked.",
    "CO": "Use the S.C.O.P.E. Feedforward Model™ or similar forward-facing methods to reframe conflicts as shared problem-solving opportunities.\nDebrief conflicts quickly and constructively to capture lessons and prevent repetition without assigning blame.\nPractise early, low-stakes conflict conversations, starting with minor disagreements to build confidence and reduce escalation.",
    "CA": "Before key meetings, research the cultural norms and communication preferences of stakeholders or teams you'll engage with.\nObserve and adapt to subtle verbal and non-verbal cues in new settings, adjusting style to maintain inclusivity.\nSeek regular cross-cultural experiences or mentorship (e.g., international projects, diverse team collaborations) to broaden adaptive range.",
    "EP": 'Pause to paraphrase others\' viewpoints before responding, ensuring their perspective is accurately understood.\nPractise a "day-in-the-life" reflection, imagining issues from a colleague\'s or stakeholder\'s perspective to build deeper empathy.\nAsk open-ended, curiosity-driven questions in meetings to surface perspectives that might otherwise remain hidden.'
}

def validate_textbank():
    """Validate that all required text bank entries exist."""
    required_dims = {"DT", "TR", "CO", "CA", "EP"}
    ks_bands = {"High", "Very High"}
    da_bands = {"Developing", "Low / Limited"}

    errors = []

    # Validate KS_TEXTS
    for dim in required_dims:
        if dim not in KS_TEXTS:
            errors.append(f"Missing dimension {dim} in KS_TEXTS")
        else:
            for band in ks_bands:
                if band not in KS_TEXTS[dim]:
                    errors.append(f"Missing band {band} for dimension {dim} in KS_TEXTS")

    # Validate DA_TEXTS
    for dim in required_dims:
        if dim not in DA_TEXTS:
            errors.append(f"Missing dimension {dim} in DA_TEXTS")
        else:
            for band in da_bands:
                if band not in DA_TEXTS[dim]:
                    errors.append(f"Missing band {band} for dimension {dim} in DA_TEXTS")

    # Validate PR_TEXTS
    for dim in required_dims:
        if dim not in PR_TEXTS:
            errors.append(f"Missing dimension {dim} in PR_TEXTS")

    if errors:
        raise ValueError(f"Text bank validation failed: {'; '.join(errors)}")

    return True

# Run validation on import
validate_textbank()